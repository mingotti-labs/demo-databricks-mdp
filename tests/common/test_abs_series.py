import json

import pytest

from common import abs_series
from common.abs_series import observation_rows, stamp, to_jsonl

HEADER = (
    "STRUCTURE,STRUCTURE_ID,STRUCTURE_NAME,ACTION,MEASURE,Measure,INDEX,Index,TSEST,"
    "Adjustment Type,REGION,Region,FREQ,Frequency,TIME_PERIOD,Time Period,OBS_VALUE,"
    "Observation Value,UNIT_MEASURE,Unit of Measure,OBS_STATUS,Observation Status,"
    "DECIMALS,Decimals,OBS_COMMENT,Observation Comment,BASE_PERIOD,Reference Base Period"
)


def line(period: str, value: str, status: str = "") -> str:
    return (
        "DATAFLOW,ABS:CPI(2.0.0),Consumer Price Index (CPI),I,1,Index numbers,10001,"
        f"All groups CPI,10,Original,50,Australia,M,Monthly,{period},,{value},,IN,"
        f"Index Numbers,{status},,,,,,25,Sep 2025 = 100.0"
    )


CSV = "\n".join([HEADER, line("2026-09", "104.34"), line("2026-07", "103.5"), line("2026-08", "")])


def test_rows_skip_empty_values_and_sort_by_period():
    rows = observation_rows("1.10001.10.50.M", CSV)
    assert [r["time_period"] for r in rows] == ["2026-07", "2026-09"]


def test_row_columns():
    row = observation_rows("1.10001.10.50.M", CSV)[1]
    assert row == {
        "series_key": "1.10001.10.50.M",
        "time_period": "2026-09",
        "value": "104.34",
        "measure": "Index numbers",
        "index": "All groups CPI",
        "adjustment_type": "Original",
        "region": "Australia",
        "frequency": "Monthly",
        "unit": "Index Numbers",
        "base_period": "Sep 2025 = 100.0",
        "obs_status": None,
    }


def test_obs_status_code_is_kept_when_present():
    text = "\n".join([HEADER, line("2026-09", "104.34", "E")])
    assert observation_rows("k", text)[0]["obs_status"] == "E"


def test_no_rows_fails_with_the_key():
    with pytest.raises(RuntimeError, match="ABS k: no rows"):
        observation_rows("k", HEADER)


class Response:
    def __init__(self, status_code: int, text: str = ""):
        self.status_code, self.text = status_code, text


def test_get_csv_returns_the_text(monkeypatch):
    calls = []

    def fake_get(url, params, timeout):
        calls.append((url, params))
        return Response(200, "csv")

    monkeypatch.setattr(abs_series.requests, "get", fake_get)
    assert abs_series.get_csv("https://x/rest", "1.2") == "csv"
    assert calls == [("https://x/rest/data/ABS,CPI,2.0.0/1.2", {"format": "csvfilewithlabels"})]


def test_get_csv_names_key_and_status_on_failure(monkeypatch):
    monkeypatch.setattr(abs_series.requests, "get", lambda *a, **k: Response(404))
    with pytest.raises(RuntimeError, match="ABS 1.2: HTTP 404"):
        abs_series.get_csv("https://x/rest", "1.2")


def test_stamp_and_jsonl():
    rows = stamp([{"a": 1}], "2026-11-03T00:00:00+00:00")
    assert rows == [{"a": 1, "ingested_timestamp": "2026-11-03T00:00:00+00:00"}]
    assert [json.loads(x) for x in to_jsonl(rows).splitlines()] == rows
