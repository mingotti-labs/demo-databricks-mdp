import csv
from pathlib import Path

from common.investments import COMPANY_FUNDAMENTALS_COMMENTS, FIGURES
from common.market_climate_sql import index_member_valuation_query

DATA = Path(__file__).resolve().parents[2] / "data" / "portfolio"
REVENUE_CONCEPTS = [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "RevenuesNetOfInterestExpense",
    "SalesRevenueNet",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
]


def test_revenue_is_a_trailing_twelve_month_figure_with_a_description():
    assert ("revenue", "duration", "USD") in FIGURES
    assert COMPANY_FUNDAMENTALS_COMMENTS["revenue"]


def test_revenue_concepts_are_mapped_in_priority_order():
    rows = [r for r in csv.DictReader(open(DATA / "concept_mapping.csv", encoding="utf-8")) if r["figure"] == "revenue"]
    ordered = [r["concept"] for r in sorted(rows, key=lambda r: int(r["priority"]))]
    assert ordered == REVENUE_CONCEPTS


def test_five_bear_funds_are_benchmarks():
    rows = csv.DictReader(open(DATA / "benchmarks.csv", encoding="utf-8"))
    assert {r["symbol"] for r in rows if r["kind"] == "bear_fund"} == {"SQQQ", "PSQ", "SH", "SDS", "SPXU"}


def test_member_query_has_price_to_sales_and_does_not_exclude_on_revenue():
    sql = index_member_valuation_query()
    assert "AS price_to_sales_ratio" in sql and "revenue_trailing_twelve_months_amount > 0" in sql
    assert "no_revenue" not in sql
    assert "revenue_trailing_twelve_months_amount >= earnings_trailing_twelve_months_amount" in sql
