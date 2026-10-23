from pathlib import Path

import pytest

from common.bronze_checks import check_table, load_spec, valid_distinct_keys_sql

SPECS = sorted((Path(__file__).resolve().parents[2] / "verification/bronze_checks").glob("*.yml"))
PLAIN = {"raw": "t_raw", "scd2": "t_scd2", "keys": ["id"], "columns": ["id"]}
OK = {"raw": 10, "valid_distinct": 10, "scd2_current": 10}


@pytest.mark.parametrize("path", SPECS, ids=lambda p: p.stem)
def test_every_spec_loads(path):
    assert load_spec(path)["source"] == path.stem


def test_valid_distinct_keys_sql_excludes_null_keys():
    sql = valid_distinct_keys_sql("c.s.t", ["a", "b"])
    assert "a IS NOT NULL AND b IS NOT NULL" in sql and "DISTINCT a, b" in sql


def test_passes_when_every_row_landed():
    assert check_table(PLAIN, OK, {"id"}) == []


def test_empty_raw_fails():
    assert check_table(PLAIN, {**OK, "raw": 0, "valid_distinct": 0, "scd2_current": 0}, {"id"})


def test_missing_and_forbidden_columns_fail():
    table = {**PLAIN, "columns": ["id", "name"], "absent_columns": ["old"]}
    failures = check_table(table, OK, {"id", "old"})
    assert any("missing" in f for f in failures) and any("gone" in f for f in failures)


def test_duplicate_keys_without_quarantine_fail():
    assert check_table(PLAIN, {**OK, "valid_distinct": 9, "scd2_current": 9}, {"id"})


def test_scd2_current_must_equal_valid_keys():
    assert check_table(PLAIN, {**OK, "scd2_current": 9}, {"id"})


def test_quarantine_accounts_for_the_rest():
    table = {**PLAIN, "quarantine": "t_quarantine"}
    counts = {"raw": 10, "valid_distinct": 7, "scd2_current": 7, "quarantine": 3}
    assert check_table(table, counts, {"id"}) == []
    assert check_table(table, {**counts, "quarantine": 2}, {"id"})


def test_quarantine_not_empty_flag():
    table = {**PLAIN, "quarantine": "q", "quarantine_not_empty": True}
    counts = {**OK, "quarantine": 0}
    assert any("empty" in f for f in check_table(table, counts, {"id"}))


def test_reference_rows_tolerance():
    table = {**PLAIN, "reference_rows": 10}
    assert check_table(table, OK, {"id"}) == []
    far = {"raw": 20, "valid_distinct": 20, "scd2_current": 20}
    assert check_table(table, far, {"id"})


def test_scd1_only_table_is_valid_and_checked():
    table = {"raw": "t_raw", "scd1": "t_scd1", "keys": ["id"], "columns": ["id"]}
    assert check_table(table, {"raw": 10, "valid_distinct": 10, "scd1_current": 10}, {"id"}) == []
    assert check_table(table, {"raw": 10, "valid_distinct": 10, "scd1_current": 9}, {"id"})


def test_scd1_checked_when_listed():
    table = {**PLAIN, "scd1": "t_scd1"}
    assert check_table(table, {**OK, "scd1_current": 10}, {"id"}) == []
    assert check_table(table, {**OK, "scd1_current": 9}, {"id"})
