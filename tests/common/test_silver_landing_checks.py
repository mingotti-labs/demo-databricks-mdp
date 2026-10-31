from pathlib import Path

import pytest
import yaml

from common.silver_landing_checks import load_entities, load_spec

ROOT = Path(__file__).resolve().parents[2]
CHECKS = ROOT / "verification/silver_landing_checks"
SPECS = sorted(CHECKS.glob("*.yml"))
GOOD = """\
source: acme
ingested_timestamp: true
tables:
  - table: customers
    bronze_schema: bronze_acme_publish
    bronze_table: customers_scd2
    scd2: true
  - table: orders
    bronze_schema: bronze_acme_publish
    bronze_table: orders_scd1
    scd2: false
"""


@pytest.mark.parametrize("path", SPECS, ids=lambda p: p.stem)
def test_every_spec_loads(path):
    assert load_spec(path)["source"] == path.stem


def test_every_source_with_a_landing_schema_has_a_file():
    patterns = yaml.safe_load(
        (ROOT / "src/common/design_patterns.yml").read_text("utf-8")
    )
    with_landing = {
        s for s, v in patterns.items() if "silver_landing" in v.get("schemas", {})
    }
    assert with_landing == {p.stem for p in SPECS}


def test_one_source_returns_its_tables_with_source_and_flag(tmp_path):
    (tmp_path / "acme.yml").write_text(GOOD, encoding="utf-8")
    entities = load_entities(tmp_path, "acme")
    assert [e["table"] for e in entities] == ["customers", "orders"]
    assert entities[0] == {
        "source": "acme",
        "ingested_timestamp": True,
        "table": "customers",
        "bronze_schema": "bronze_acme_publish",
        "bronze_table": "customers_scd2",
        "scd2": True,
    }


def test_empty_source_returns_every_file(tmp_path):
    (tmp_path / "acme.yml").write_text(GOOD, encoding="utf-8")
    (tmp_path / "beta.yml").write_text(GOOD.replace("acme", "beta"), encoding="utf-8")
    assert {e["source"] for e in load_entities(tmp_path)} == {"acme", "beta"}


def test_a_source_with_no_file_fails_naming_it(tmp_path):
    with pytest.raises(ValueError, match="'nope'"):
        load_entities(tmp_path, "nope")


def test_source_must_match_the_file_name(tmp_path):
    (tmp_path / "other.yml").write_text(GOOD, encoding="utf-8")
    with pytest.raises(ValueError, match="not the file name"):
        load_spec(tmp_path / "other.yml")


def test_a_table_with_a_missing_or_unknown_key_fails(tmp_path):
    (tmp_path / "acme.yml").write_text(
        GOOD.replace("    scd2: false\n", ""), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="orders"):
        load_spec(tmp_path / "acme.yml")
    (tmp_path / "acme.yml").write_text(GOOD + "    extra: 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="orders"):
        load_spec(tmp_path / "acme.yml")
