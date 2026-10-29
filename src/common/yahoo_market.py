# Helpers for the Yahoo Finance fetch (src/common/fetch_yahoo.py): which days to
# fetch per symbol, and rows from yfinance's pandas results, values as text. No
# network here; the notebook calls yfinance and writes the JSON Lines files.
import json
import math
from datetime import date, timedelta

NEW_SYMBOL_DAYS = 365
PRICE_COLUMNS = {
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Adj Close": "adj_close",
    "Volume": "volume",
}
EVENT_COLUMNS = {"Dividends": "dividend", "Stock Splits": "split"}


def yahoo_symbol(symbol: str) -> str:
    """Yahoo writes a share class with a dash: BRK.B is BRK-B."""
    return symbol.replace(".", "-")


def text(value) -> str | None:
    """A value as text, as Yahoo sent it; missing (None or NaN) stays missing."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return str(value)


def plan(
    state: dict | None, reload_symbols: set[str], symbol: str, today: date
) -> tuple[date, bool]:
    """First day to fetch and whether it is a full reload.

    A new symbol loads one year; a symbol named in reload_symbols (or `*`) reloads
    from its first stored day; otherwise fetch from the last stored day minus one,
    which rewrites a day stored while the market was open.
    """
    if not state or not state.get("last_price_date"):
        return today - timedelta(days=NEW_SYMBOL_DAYS), True
    if symbol in reload_symbols or "*" in reload_symbols:
        return date.fromisoformat(state["first_price_date"]), True
    return date.fromisoformat(state["last_price_date"]) - timedelta(days=1), False


def has_new_event(frame, last_price_date: str) -> bool:
    """A dividend or split after the last stored day: Yahoo restated earlier prices."""
    last = date.fromisoformat(last_price_date)
    for column in EVENT_COLUMNS:
        if column in frame and any(
            ts.date() > last for ts, value in frame[column].items() if value and value > 0
        ):
            return True
    return False


def price_rows(symbol: str, frame) -> list[dict]:
    """One row per trading day with a close."""
    rows = []
    days = frame.dropna(subset=["Close"])
    for ts, values in zip(days.index, days.to_dict("records"), strict=True):
        row = {
            "symbol": symbol,
            "yahoo_symbol": yahoo_symbol(symbol),
            "date": ts.date().isoformat(),
        }
        row.update({name: text(values.get(column)) for column, name in PRICE_COLUMNS.items()})
        rows.append(row)
    return rows


def event_rows(symbol: str, frame) -> list[dict]:
    """One row per dividend or split; the date is the day in the exchange's time zone."""
    rows = []
    for column, event_type in EVENT_COLUMNS.items():
        if column not in frame:
            continue
        for ts, value in frame[column].items():
            if value and value > 0:
                rows.append(
                    {
                        "symbol": symbol,
                        "yahoo_symbol": yahoo_symbol(symbol),
                        "date": ts.date().isoformat(),
                        "event_type": event_type,
                        "value": text(value),
                    }
                )
    return rows


def calendar_row(symbol: str, calendar: dict) -> dict:
    """The next announced ex-date, pay date (Yahoo's `Dividend Date`) and earnings date."""
    earnings = calendar.get("Earnings Date") or []
    return {
        "symbol": symbol,
        "yahoo_symbol": yahoo_symbol(symbol),
        "ex_dividend_date": text(calendar.get("Ex-Dividend Date")),
        "dividend_date": text(calendar.get("Dividend Date")),
        "earnings_date": text(earnings[0]) if earnings else None,
    }


def monthly_expiry(expiries, today: date) -> str | None:
    """The first expiry from today that is a third Friday (a Friday on the 15th to 21st)."""
    for expiry in expiries:
        day = date.fromisoformat(expiry)
        if day >= today and day.weekday() == 4 and 15 <= day.day <= 21:
            return expiry
    return None


def option_row(symbol: str, expiries, expiry: str | None, chain) -> dict:
    """Whether options are listed, and open interest and volume on the monthly expiry."""
    row = {
        "symbol": symbol,
        "yahoo_symbol": yahoo_symbol(symbol),
        "has_options": text(len(expiries) > 0),
        "expiry_count": text(len(expiries)),
        "nearest_monthly_expiry": expiry,
        "open_interest": None,
        "volume": None,
    }
    if chain is not None:
        for field in ("open_interest", "volume"):
            column = "openInterest" if field == "open_interest" else "volume"
            total = chain.calls[column].fillna(0).sum() + chain.puts[column].fillna(0).sum()
            row[field] = text(int(total))
    return row


def stamp(rows: list[dict], ingested: str) -> list[dict]:
    """Add the fetch time to every row."""
    return [row | {"ingested_timestamp": ingested} for row in rows]


def to_jsonl(rows: list[dict]) -> str:
    return "".join(json.dumps(row) + "\n" for row in rows)
