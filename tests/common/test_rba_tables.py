import json
from datetime import date

import pytest

from common.rba_tables import first_day, parse_date, parse_table, since, stamp, to_jsonl

DAILY = """﻿F11.1  EXCHANGE RATES
Title,A$1=USD,Trade-weighted Index May 1970 = 100,"A$1=XXX, comma"
Description,AUD/USD Exchange Rate,Australian Dollar Trade-weighted Index,
Frequency,Daily,Daily,Daily
Type,Indicative,Indicative,Indicative
Units,USD,Index,XXX


Source,WM/Reuters,RBA,RBA
Publication date,30-Oct-2026,30-Oct-2026,01-Oct-2024
Series ID,FXRUSD,FXRTWI,FXRXXX
03-Jan-2023,0.6828,61.40,
04-Jan-2023,0.6809,,
05-Jan-2023,0.6815,61.50,3.1
"""


def test_one_row_per_series_and_date_with_empty_cells_skipped():
    rows = parse_table("F11.1", DAILY)
    assert [(r["series_id"], r["observation_date"], r["value"]) for r in rows] == [
        ("FXRUSD", "03-Jan-2023", "0.6828"),
        ("FXRTWI", "03-Jan-2023", "61.40"),
        ("FXRUSD", "04-Jan-2023", "0.6809"),
        ("FXRUSD", "05-Jan-2023", "0.6815"),
        ("FXRTWI", "05-Jan-2023", "61.50"),
        ("FXRXXX", "05-Jan-2023", "3.1"),
    ]


def test_rows_carry_the_series_header():
    row = parse_table("F11.1", DAILY)[0]
    assert row == {
        "table_id": "F11.1",
        "series_id": "FXRUSD",
        "observation_date": "03-Jan-2023",
        "value": "0.6828",
        "title": "A$1=USD",
        "description": "AUD/USD Exchange Rate",
        "frequency": "Daily",
        "type": "Indicative",
        "units": "USD",
        "source": "WM/Reuters",
        "publication_date": "30-Oct-2026",
    }


def test_missing_header_text_is_none_and_quoted_commas_survive():
    row = next(r for r in parse_table("F11.1", DAILY) if r["series_id"] == "FXRXXX")
    assert row["description"] is None
    assert row["title"] == "A$1=XXX, comma"


def test_missing_series_id_row_fails():
    with pytest.raises(ValueError, match="no 'Series ID' row"):
        parse_table("F1", "F1 RATES\nTitle,Cash Rate Target\n04-Jan-2011,4.75\n")


def test_data_row_without_a_date_fails():
    with pytest.raises(ValueError):
        parse_table("F1", "Series ID,A\nnot a date,1\n")


def test_parse_date_ignores_the_locale():
    assert parse_date("03-Jan-2023") == date(2023, 1, 3)
    assert parse_date("31-Dec-1959") == date(1959, 12, 31)


def test_first_day_is_31_days_before_the_last_stored_date():
    assert first_day(date(2026, 10, 23), reload=False) == date(2026, 9, 22)


def test_first_day_is_none_for_a_new_table_or_a_reload():
    assert first_day(None, reload=False) is None
    assert first_day(date(2026, 10, 23), reload=True) is None


def test_since_keeps_rows_on_or_after_the_first_day():
    rows = parse_table("F11.1", DAILY)
    kept = since(rows, date(2023, 1, 4))
    assert {r["observation_date"] for r in kept} == {"04-Jan-2023", "05-Jan-2023"}
    assert since(rows, None) == rows


def test_stamp_and_jsonl():
    rows = stamp([{"a": "1"}], "2026-10-31T00:00:00+00:00")
    assert rows == [{"a": "1", "ingested_timestamp": "2026-10-31T00:00:00+00:00"}]
    assert json.loads(to_jsonl(rows)) == rows[0]
