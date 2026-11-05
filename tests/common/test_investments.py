import csv
import hashlib
from pathlib import Path

import pytest

from common.investments import (
    CPI_RATES,
    FIGURES,
    RATES,
    YAHOO_EXCHANGE_TO_MARKET,
    entity_id,
    entity_id_sql,
    figure_columns_sql,
    figure_names,
    schema_with_comments,
    COMPANY_FUNDAMENTALS_COMMENTS,
    US_CPI_SERIES_ID,
    market_code_sql,
)

MAPPING = Path(__file__).parents[2] / "data" / "portfolio" / "concept_mapping.csv"


def test_figure_list_matches_concept_mapping():
    with MAPPING.open(encoding="utf-8", newline="") as file:
        mapped = {row["figure"] for row in csv.DictReader(file)}
    assert set(figure_names()) == mapped
    assert len(figure_names()) == len(set(figure_names()))


def test_every_figure_kind_and_unit_is_known():
    assert {kind for _, kind, _ in FIGURES} == {"instant", "duration", "cover", "period"}
    assert {unit for _, _, unit in FIGURES} == {"USD", "USD/shares", "shares"}


def test_entity_id_is_the_sha256_of_the_joined_parts():
    expected = hashlib.sha256(b"sec:0000320193").hexdigest()
    assert entity_id("sec", "0000320193") == expected
    assert len(expected) == 64


def test_entity_id_skips_empty_parts_as_concat_ws_does():
    assert entity_id("", "SPY") == entity_id("SPY")


def test_entity_id_sql_hashes_the_columns():
    assert entity_id_sql("a", "b") == "sha2(concat_ws(':', a, b), 256)"


def test_market_code_sql_maps_every_exchange_code():
    sql = market_code_sql("exchange_code")
    for code, market in YAHOO_EXCHANGE_TO_MARKET.items():
        assert f"WHEN '{code}' THEN '{market}'" in sql
    assert set(YAHOO_EXCHANGE_TO_MARKET.values()) == {"XNAS", "XNYS", "XCBO", "XNYM", "XXXX"}


def test_commodity_exchanges_map_to_a_market_or_to_no_market():
    assert {c: YAHOO_EXCHANGE_TO_MARKET[c] for c in ("CMX", "NYM", "FGI", "SNP", "NYB")} == {
        "CMX": "XNYM",
        "NYM": "XNYM",
        "FGI": "XXXX",
        "SNP": "XXXX",
        "NYB": "XXXX",
    }


def test_rate_codes_are_unique_and_spelled_out():
    codes = [code for code, _, _, _, _ in RATES]
    assert len(codes) == len(set(codes)) == 6
    assert "australian_dollar_in_us_dollars" in codes


def test_cpi_rate_codes_are_unique_and_do_not_overlap_the_daily_rates():
    cpi_codes = [code for code, *_ in CPI_RATES]
    assert len(cpi_codes) == len(set(cpi_codes)) == 5
    assert not set(cpi_codes) & {code for code, *_ in RATES}
    assert all(unit == "index_points" for *_, unit in CPI_RATES)


def test_figure_columns_sql_has_one_column_per_figure():
    sql = figure_columns_sql()
    for figure in figure_names():
        assert f"AS {figure}" in sql
    assert "CAST(ROUND(value) AS BIGINT)" in sql


def test_schema_with_comments_describes_only_the_named_columns_and_escapes_quotes():
    ddl = schema_with_comments([("a", "decimal(10,2)"), ("b", "string")], {"a": "the company's amount"})
    assert ddl == "`a` decimal(10,2) COMMENT 'the company" + chr(92) + "'s amount', `b` string"


def test_schema_with_comments_rejects_a_description_for_a_missing_column():
    with pytest.raises(ValueError):
        schema_with_comments([("a", "string")], {"gone": "x"})


def test_us_cpi_series_is_one_of_the_cpi_series():
    assert US_CPI_SERIES_ID in [series for _, _, _, series, _ in CPI_RATES]
    assert COMPANY_FUNDAMENTALS_COMMENTS["earnings_ten_year_average_amount"]
