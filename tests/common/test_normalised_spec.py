import copy
from pathlib import Path

import pytest

from common.normalised_spec import (
    SpecError,
    check,
    drift,
    load_spec,
    match_key,
    tables,
    unpivot_columns,
)

SPECS = Path(__file__).parents[2] / "src/layers/silver/normalised/specs"

SPEC = {
    "source_system": "acme",
    "base_entities": {
        "customers": {
            "from": "silver_landing_acme.customers",
            "natural_key": ["id"],
            "columns": ["name"],
            "extracted": {"country": "country", "state": "state"},
        }
    },
    "bridge_entities": {
        "customers_tag": {
            "from": "silver_landing_acme.customers",
            "parent": "customers",
            "explode": {"column": "tags", "split": ";"},
            "extracted": "tag",
        },
        "customers_channel": {
            "from": "silver_landing_acme.customers",
            "parent": "customers",
            "unpivot": {"columns_like": "via_%", "keep_when": "Y"},
        },
    },
    "extracted_entities": {"country": {}, "state": {"parent": "country"}, "tag": {}},
    "ignored_columns": ["customers.notes"],
}


def spec_with(change) -> dict:
    spec = copy.deepcopy(SPEC)
    change(spec)
    return spec


def test_valid_spec_has_no_problems():
    assert check(SPEC) == []


@pytest.mark.parametrize("path", sorted(SPECS.glob("*.yml")), ids=lambda p: p.stem)
def test_repo_specs_load(path):
    load_spec(str(path))


def test_load_spec_raises_on_problem(tmp_path):
    path = tmp_path / "bad.yml"
    path.write_text(
        "source_system: acme\nbase_entities:\n  c:\n    from: silver_landing_other.c\n"
        "    natural_key: [id]\n    columns: []\nignored_columns: []\n"
    )
    with pytest.raises(SpecError, match="outside silver_landing_acme"):
        load_spec(str(path))


@pytest.mark.parametrize(
    "change, message",
    [
        (
            lambda s: s["base_entities"]["customers"].update(
                {"from": "silver_landing_other.customers"}
            ),
            "outside",
        ),
        (
            lambda s: s["extracted_entities"].update({"customers": {}}),
            "used more than once",
        ),
        (lambda s: s["extracted_entities"].update({"value_lineage": {}}), "reserved"),
        (
            lambda s: s["bridge_entities"]["customers_tag"].update(
                {"parent": "orders"}
            ),
            "not a base entity",
        ),
        (
            lambda s: s["bridge_entities"]["customers_tag"].update(
                {"from": "silver_landing_acme.orders"}
            ),
            "differs",
        ),
        (lambda s: s["extracted_entities"].pop("tag"), "not declared"),
        (
            lambda s: s["extracted_entities"].update({"currency": {}}),
            "no member column",
        ),
        (
            lambda s: s["extracted_entities"]["state"].update({"parent": "region"}),
            "not an extracted entity",
        ),
        (
            lambda s: s["extracted_entities"]["country"].update({"parent": "state"}),
            "cycle",
        ),
        (
            lambda s: s["base_entities"]["customers"]["extracted"].pop("country"),
            "exactly one column",
        ),
        (
            lambda s: s["extracted_entities"]["tag"].update(
                {"attributes": ["tag_name"]}
            ),
            "bridge members",
        ),
        (
            lambda s: s.update(
                {
                    "dependency_tolerance": [
                        {
                            "entity": "customers",
                            "determinant": "state",
                            "dependent": "zip",
                            "max_violations": 1,
                        }
                    ]
                }
            ),
            "zip is not used",
        ),
        (
            lambda s: s["ignored_columns"].append("customers.name"),
            "both used and ignored",
        ),
    ],
)
def test_cross_reference_problem(change, message):
    problems = check(spec_with(change))
    assert any(message in p for p in problems), problems


@pytest.mark.parametrize(
    "value, expected",
    [
        ("Vitória da Conquista", "VITORIA DA CONQUISTA"),
        ("  AuStRaLiA ", "AUSTRALIA"),
        ("São   Paulo", "SAO PAULO"),
        (None, None),
    ],
)
def test_match_key(value, expected):
    assert match_key(value) == expected


def test_tables_and_kinds():
    spec = spec_with(
        lambda s: s.update(
            {
                "dependency_tolerance": [
                    {
                        "entity": "customers",
                        "determinant": "state",
                        "dependent": "country",
                        "max_violations": 1,
                    }
                ]
            }
        )
    )
    assert tables(spec) == {
        "customers": "base",
        "customers_quarantine": None,
        "customers_tag": "bridge",
        "customers_channel": "bridge",
        "country": "extracted",
        "state": "extracted",
        "tag": "extracted",
        "value_lineage": None,
    }


LANDING = {
    "customers": [
        "id",
        "name",
        "country",
        "state",
        "tags",
        "via_web",
        "via_phone",
        "notes",
        "is_current",
    ]
}


def test_drift_clean():
    assert drift(SPEC, LANDING) == []


def test_drift_new_column():
    landing = {"customers": LANDING["customers"] + ["email"]}
    assert drift(SPEC, landing) == ["customers.email: neither used nor ignored"]


def test_drift_new_flag_column_is_picked_up_by_unpivot():
    landing = {"customers": LANDING["customers"] + ["via_email"]}
    assert drift(SPEC, landing) == []


def test_drift_missing_column():
    landing = {"customers": [c for c in LANDING["customers"] if c != "name"]}
    assert drift(SPEC, landing) == [
        "customers.name: used by the spec but missing in Landing"
    ]


# unpivot.columns (v0.2): an explicit list, for a flag family sharing no
# name prefix (acnc's purpose/beneficiary flags, see phase4e's design.md).
SPEC_WITH_COLUMNS_UNPIVOT = spec_with(
    lambda s: s["bridge_entities"].update(
        {
            "customers_purpose": {
                "from": "silver_landing_acme.customers",
                "parent": "customers",
                "unpivot": {"columns": ["is_retail", "wholesale"], "keep_when": "Y"},
            }
        }
    )
)


def test_unpivot_columns_explicit_list_ignores_landing_columns():
    unpivot = {"columns": ["is_retail", "wholesale"], "keep_when": "Y"}
    assert unpivot_columns(unpivot, ["is_retail", "other_column"]) == [
        "is_retail",
        "wholesale",
    ]


def test_unpivot_columns_like_pattern_matches_landing_columns():
    unpivot = {"columns_like": "via_%", "keep_when": "Y"}
    assert unpivot_columns(unpivot, ["via_web", "via_phone", "other"]) == [
        "via_web",
        "via_phone",
    ]


def test_check_allows_columns_unpivot():
    assert check(SPEC_WITH_COLUMNS_UNPIVOT) == []


def test_drift_columns_unpivot_no_shared_prefix():
    landing = {"customers": LANDING["customers"] + ["is_retail", "wholesale"]}
    assert drift(SPEC_WITH_COLUMNS_UNPIVOT, landing) == []


def test_drift_columns_unpivot_missing_landing_column():
    landing = {"customers": LANDING["customers"] + ["is_retail"]}
    assert drift(SPEC_WITH_COLUMNS_UNPIVOT, landing) == [
        "customers.wholesale: used by the spec but missing in Landing"
    ]
