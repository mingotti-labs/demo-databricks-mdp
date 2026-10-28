"""P8 (yahoo-market-data P1): keys, shapes and times of the four Yahoo datasets.

For 20 symbols (including BRK-B, REITs, a non-payer and both benchmarks):
prices (bulk 1y), dividends, calendar and options. Reports rows, duplicate and
empty keys, the calendar's real field names and value types, and the time per
dataset.
"""

import logging
import time
from collections import Counter
from datetime import date

import yfinance as yf

logging.getLogger("yfinance").setLevel(logging.CRITICAL)
SYMBOLS = [
    "AAPL", "MSFT", "JNJ", "KO", "PG", "XOM", "JPM", "O", "PLD", "SPG",
    "NEE", "T", "ABBV", "BRK-B", "GOOGL", "GOOG", "AMZN", "TSLA", "SPY", "NOBL",
]


def timed(label, fn):
    start = time.monotonic()
    result = fn()
    print(f"\n== {label}: {time.monotonic() - start:.1f}s")
    return result


def report_keys(label, keys):
    counts = Counter(keys)
    dups = [k for k, n in counts.items() if n > 1]
    empty = [k for k in keys if any(part in (None, "") for part in k)]
    print(f"{label}: rows {len(keys)}, duplicate keys {len(dups)} {dups[:3]}, empty keys {len(empty)}")


def monthly(expiries):
    for expiry in expiries:
        day = date.fromisoformat(expiry)
        if day >= date.today() and day.weekday() == 4 and 15 <= day.day <= 21:
            return expiry
    return None


def main():
    print("yfinance", yf.__version__)
    prices = timed("prices", lambda: yf.download(
        SYMBOLS, period="1y", auto_adjust=False, actions=False,
        group_by="ticker", threads=True, progress=False,
    ))
    print("columns level 1:", sorted(set(prices.columns.get_level_values(1))))
    keys = []
    for s in SYMBOLS:
        frame = prices[s].dropna(subset=["Close"])
        keys += [(s, str(d.date())) for d in frame.index]
        if s in ("AAPL", "SPY"):
            print(s, "rows", len(frame), "first", frame.index.min(), "last", frame.index.max(),
                  "tz", frame.index.tz, "sample", frame.iloc[-1].to_dict())
    report_keys("prices", keys)

    def dividends():
        out = {}
        for s in SYMBOLS:
            out[s] = yf.Ticker(s).dividends
        return out
    divs = timed("dividends", dividends)
    keys = [(s, str(d.date())) for s, series in divs.items() for d in series.index]
    report_keys("dividends", keys)
    print("payers", sum(1 for v in divs.values() if len(v)), "non-payers",
          [s for s, v in divs.items() if not len(v)], "index tz", divs["KO"].index.tz,
          "KO last", divs["KO"].tail(2).to_dict())

    def calendars():
        out = {}
        for s in SYMBOLS:
            try:
                out[s] = yf.Ticker(s).calendar
            except Exception as error:  # noqa: BLE001 - the probe reports every failure
                out[s] = f"ERROR {type(error).__name__}: {error}"
        return out
    cals = timed("calendar", calendars)
    fields = Counter(k for v in cals.values() if isinstance(v, dict) for k in v)
    print("calendar fields:", dict(fields))
    for s in ("KO", "O", "AMZN", "SPY", "BRK-B"):
        value = cals[s]
        print(s, {k: (type(v).__name__, v) for k, v in value.items()} if isinstance(value, dict) else value)

    def options():
        out = {}
        for s in SYMBOLS:
            ticker = yf.Ticker(s)
            expiries = ticker.options
            expiry = monthly(expiries)
            oi = None
            if expiry:
                chain = ticker.option_chain(expiry)
                oi = int(chain.calls["openInterest"].fillna(0).sum() + chain.puts["openInterest"].fillna(0).sum())
            out[s] = (len(expiries), expiry, oi)
        return out
    opts = timed("options", options)
    print({s: v for s, v in opts.items()})


main()
