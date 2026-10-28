import json
from datetime import date
from types import SimpleNamespace

import pandas as pd

from common.yahoo_market import (
    calendar_row,
    event_rows,
    has_new_event,
    monthly_expiry,
    option_row,
    plan,
    price_rows,
    stamp,
    to_jsonl,
    yahoo_symbol,
)

TODAY = date(2026, 10, 29)
NY = "America/New_York"


def prices(days, dividends=None, splits=None):
    index = pd.DatetimeIndex(days).tz_localize(NY)
    n = len(days)
    return pd.DataFrame(
        {
            "Open": [1.0] * n,
            "High": [2.0] * n,
            "Low": [0.5] * n,
            "Close": [1.5] * n,
            "Adj Close": [1.25] * n,
            "Volume": [100] * n,
            "Dividends": dividends or [0.0] * n,
            "Stock Splits": splits or [0.0] * n,
        },
        index=index,
    )


def test_yahoo_symbol():
    assert yahoo_symbol("BRK.B") == "BRK-B"
    assert yahoo_symbol("^VIX") == "^VIX"


def test_plan():
    state = {"first_price_date": "2025-10-29", "last_price_date": "2026-10-23"}
    assert plan(None, set(), "KO", TODAY) == (date(2025, 10, 29), True)
    assert plan(state, set(), "KO", TODAY) == (date(2026, 10, 22), False)
    assert plan(state, {"KO"}, "KO", TODAY) == (date(2025, 10, 29), True)
    assert plan(state, {"*"}, "KO", TODAY) == (date(2025, 10, 29), True)
    assert plan(state, {"AAPL"}, "KO", TODAY) == (date(2026, 10, 22), False)


def test_has_new_event_only_after_last_stored_day():
    frame = prices(["2026-10-22", "2026-10-23", "2026-10-26"], dividends=[0.51, 0.0, 0.0])
    assert not has_new_event(frame, "2026-10-23")
    frame = prices(["2026-10-22", "2026-10-23", "2026-10-26"], splits=[0.0, 0.0, 10.0])
    assert has_new_event(frame, "2026-10-23")


def test_price_rows_skip_days_without_close():
    frame = prices(["2026-10-22", "2026-10-23"])
    frame.loc[frame.index[1], "Close"] = float("nan")
    rows = price_rows("BRK.B", frame)
    assert rows == [
        {
            "symbol": "BRK.B",
            "yahoo_symbol": "BRK-B",
            "date": "2026-10-22",
            "open": "1.0",
            "high": "2.0",
            "low": "0.5",
            "close": "1.5",
            "adj_close": "1.25",
            "volume": "100",
        }
    ]


def test_event_rows_from_actions():
    index = pd.DatetimeIndex(["2024-03-05 09:30", "2024-06-10 09:30"]).tz_localize(NY)
    actions = pd.DataFrame({"Dividends": [0.004, 0.0], "Stock Splits": [0.0, 10.0]}, index=index)
    assert event_rows("NVDA", actions) == [
        {
            "symbol": "NVDA",
            "yahoo_symbol": "NVDA",
            "date": "2024-03-05",
            "event_type": "dividend",
            "value": "0.004",
        },
        {
            "symbol": "NVDA",
            "yahoo_symbol": "NVDA",
            "date": "2024-06-10",
            "event_type": "split",
            "value": "10.0",
        },
    ]


def test_calendar_row():
    calendar = {
        "Dividend Date": date(2026, 12, 15),
        "Ex-Dividend Date": date(2026, 11, 28),
        "Earnings Date": [date(2027, 2, 10), date(2027, 2, 14)],
        "Earnings Average": 0.7,
    }
    assert calendar_row("KO", calendar) == {
        "symbol": "KO",
        "yahoo_symbol": "KO",
        "ex_dividend_date": "2026-11-28",
        "dividend_date": "2026-12-15",
        "earnings_date": "2027-02-10",
    }
    assert calendar_row("SPY", {})["dividend_date"] is None


def test_monthly_expiry():
    expiries = ("2026-10-30", "2026-11-06", "2026-11-20", "2026-12-18")
    assert monthly_expiry(expiries, TODAY) == "2026-11-20"
    assert monthly_expiry(("2026-10-30",), TODAY) is None


def test_option_row():
    chain = SimpleNamespace(
        calls=pd.DataFrame({"openInterest": [0, 0], "volume": [10.0, float("nan")]}),
        puts=pd.DataFrame({"openInterest": [0], "volume": [5.0]}),
    )
    row = option_row("AAPL", ("2026-11-20",), "2026-11-20", chain)
    assert row["has_options"] == "True"
    assert row["open_interest"] == "0"
    assert row["volume"] == "15"
    empty = option_row("^VIX", (), None, None)
    assert empty["has_options"] == "False" and empty["volume"] is None


def test_stamp_and_jsonl():
    rows = stamp([{"symbol": "KO"}], "2026-10-29T00:00:00+00:00")
    lines = to_jsonl(rows).splitlines()
    assert json.loads(lines[0]) == {
        "symbol": "KO",
        "ingested_timestamp": "2026-10-29T00:00:00+00:00",
    }
