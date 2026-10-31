import json
import traceback
from datetime import date

import pytest
import requests

from common import fred_series
from common.fred_series import (
    first_day,
    get_json,
    observation_rows,
    series_info,
    stamp,
    to_jsonl,
)

KEY = "SECRETKEY123"
SERIES = {
    "seriess": [
        {
            "id": "DGS10",
            "title": "Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity",
            "units": "Percent",
            "frequency": "Daily",
            "notes": "ignored",
        }
    ]
}
OBSERVATIONS = {
    "observations": [
        {
            "realtime_start": "2026-10-30",
            "realtime_end": "2026-10-30",
            "date": "1962-02-09",
            "value": "4.08",
        },
        {
            "realtime_start": "2026-10-30",
            "realtime_end": "2026-10-30",
            "date": "1962-02-12",
            "value": ".",
        },
        {
            "realtime_start": "2026-10-30",
            "realtime_end": "2026-10-30",
            "date": "2026-10-29",
            "value": "4.98",
        },
    ]
}


class Response:
    def __init__(self, status, body=None, text=""):
        self.status_code, self._body, self.text = status, body, text

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


def test_series_info_keeps_title_units_frequency_only():
    assert series_info(SERIES) == {
        "title": "Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity",
        "units": "Percent",
        "frequency": "Daily",
    }


def test_missing_values_are_skipped_and_realtime_columns_dropped():
    rows = observation_rows("DGS10", series_info(SERIES), OBSERVATIONS)
    assert [(r["observation_date"], r["value"]) for r in rows] == [
        ("1962-02-09", "4.08"),
        ("2026-10-29", "4.98"),
    ]
    assert rows[1] == {
        "series_id": "DGS10",
        "observation_date": "2026-10-29",
        "value": "4.98",
        "title": "Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity",
        "units": "Percent",
        "frequency": "Daily",
    }


def test_a_payload_missing_a_key_fails():
    with pytest.raises(KeyError):
        observation_rows(
            "DGS10", series_info(SERIES), {"observations": [{"date": "2026-10-29"}]}
        )


def test_first_day_is_31_days_before_the_last_stored_date():
    assert first_day(date(2026, 10, 29), reload=False) == date(2026, 9, 28)


def test_first_day_is_none_for_a_new_series_or_a_reload():
    assert first_day(None, reload=False) is None
    assert first_day(date(2026, 10, 29), reload=True) is None


def test_stamp_and_jsonl():
    rows = stamp([{"a": "1"}], "2026-10-31T00:00:00+00:00")
    assert rows == [{"a": "1", "ingested_timestamp": "2026-10-31T00:00:00+00:00"}]
    assert json.loads(to_jsonl(rows)) == rows[0]


def test_get_json_sends_the_key_and_series(monkeypatch):
    seen = {}

    def fake_get(url, params, timeout):
        seen.update(url=url, params=params)
        return Response(200, {"ok": True})

    monkeypatch.setattr(fred_series.requests, "get", fake_get)
    assert get_json(
        "https://x/fred", KEY, "series", "DGS10", observation_start="2026-09-28"
    ) == {"ok": True}
    assert seen["url"] == "https://x/fred/series"
    assert seen["params"] == {
        "api_key": KEY,
        "file_type": "json",
        "series_id": "DGS10",
        "observation_start": "2026-09-28",
    }


def test_an_error_status_names_the_request_and_fred_message_not_the_key(monkeypatch):
    body = {
        "error_code": 400,
        "error_message": "Bad Request.  Invalid value for variable series_id.",
    }
    monkeypatch.setattr(
        fred_series.requests, "get", lambda *a, **k: Response(400, body)
    )
    with pytest.raises(RuntimeError) as error:
        get_json("https://x/fred", KEY, "series/observations", "NOPE")
    assert "FRED series/observations NOPE: HTTP 400 Bad Request" in str(error.value)
    assert KEY not in str(error.value)


def test_a_non_json_error_still_names_the_status(monkeypatch):
    monkeypatch.setattr(
        fred_series.requests, "get", lambda *a, **k: Response(503, None, "<html>")
    )
    with pytest.raises(RuntimeError, match="HTTP 503"):
        get_json("https://x/fred", KEY, "series", "DGS10")


def test_a_connection_error_never_leaks_the_key_in_the_message_or_traceback(
    monkeypatch,
):
    def fail(url, params, timeout):
        raise requests.ConnectionError(
            f"Max retries exceeded with url: /fred/series?api_key={KEY}"
        )

    monkeypatch.setattr(fred_series.requests, "get", fail)
    with pytest.raises(RuntimeError) as error:
        get_json("https://x/fred", KEY, "series", "DGS10")
    rendered = "".join(traceback.format_exception(error.value))
    assert "ConnectionError" in rendered
    assert KEY not in rendered
