import csv
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[2] / "data" / "portfolio"

DATASETS = {
    "concept_mapping": (
        ["figure", "priority", "taxonomy", "concept"],
        ["figure", "taxonomy", "concept"],
    ),
    "predecessor_ciks": (["cik", "predecessor_cik", "company", "reason"], ["cik"]),
    "settings": (["setting", "value", "currency_code", "description"], ["setting"]),
    "risk_levels": (
        [
            "level",
            "sort_order",
            "min_years_increases",
            "max_payout_ratio",
            "max_net_debt_to_ebitda",
            "min_yield",
            "max_yield",
            "min_chowder",
            "min_chowder_utilities",
            "min_dividend_growth_5y",
        ],
        ["level"],
    ),
    "target_mix": (["level", "target_weight"], ["level"]),
}


def rows(dataset: str) -> tuple[list[str], list[dict]]:
    with (DATA / f"{dataset}.csv").open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


@pytest.mark.parametrize("dataset", DATASETS)
def test_columns_and_unique_key(dataset):
    columns, keys = DATASETS[dataset]
    fieldnames, data = rows(dataset)
    assert fieldnames == columns
    assert data
    key_values = [tuple(row[k] for k in keys) for row in data]
    assert len(key_values) == len(set(key_values))
    assert all(all(part for part in key) for key in key_values)


def test_target_mix_sums_to_one():
    _, data = rows("target_mix")
    assert sum(float(row["target_weight"]) for row in data) == pytest.approx(1.0)


def test_every_mix_level_has_a_risk_level():
    _, mix = rows("target_mix")
    _, levels = rows("risk_levels")
    assert {r["level"] for r in mix} == {r["level"] for r in levels}


def test_every_figure_has_a_first_priority_concept():
    _, data = rows("concept_mapping")
    figures = {row["figure"] for row in data}
    first = {row["figure"] for row in data if row["priority"] == "1"}
    assert figures == first
