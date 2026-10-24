"""P6: does yfinance fetch the full S&P 500 from serverless without being blocked?

Prices (bulk), full dividend history and listed options per ticker, open
interest for a sample, and whether a bulk call returns full dividend history.
"""

import logging
import time
from collections import Counter
from datetime import date, timedelta
from io import StringIO

import pandas as pd
import requests
import yfinance as yf

logging.getLogger("yfinance").setLevel(logging.CRITICAL)
WIKIPEDIA = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
HEADERS = {"User-Agent": "mdp handsonessential@gmail.com"}


def tickers() -> list[str]:
    html = requests.get(WIKIPEDIA, headers=HEADERS, timeout=30).text
    table = pd.read_html(StringIO(html), attrs={"id": "constituents"}, flavor="lxml")[0]
    return [symbol.replace(".", "-") for symbol in table["Symbol"]]


def per_ticker(symbols: list[str], fetch) -> tuple[dict, Counter]:
    """Call fetch(Ticker) for each symbol; return results and error counts."""
    results, errors = {}, Counter()
    for symbol in symbols:
        try:
            results[symbol] = fetch(yf.Ticker(symbol))
        except Exception as error:  # noqa: BLE001 - the probe counts every failure by type
            errors[f"{type(error).__name__}: {str(error)[:80]}"] += 1
    return results, errors


def third_friday_on_or_after(today: date, expiries: tuple) -> str | None:
    for expiry in expiries:
        day = date.fromisoformat(expiry)
        if day >= today and day.weekday() == 4 and 15 <= day.day <= 21:
            return expiry
    return None


def main() -> None:
    symbols = tickers()
    print("yfinance", yf.__version__, "tickers", len(symbols))

    start = time.monotonic()
    prices = yf.download(
        symbols,
        period="1y",
        auto_adjust=False,
        actions=True,
        group_by="ticker",
        threads=True,
        progress=False,
    )
    closes = {
        s: prices[s]["Close"].dropna()
        for s in symbols
        if s in prices.columns.get_level_values(0)
    }
    empty = [s for s in symbols if s not in closes or closes[s].empty]
    days = Counter(len(c) for c in closes.values())
    print(
        f"\nbulk 1y prices: {time.monotonic() - start:.0f}s, shape {prices.shape}, no data {len(empty)} {empty[:20]}"
    )
    print("trading days per ticker (top)", days.most_common(3))

    start = time.monotonic()
    dividends, errors = per_ticker(symbols, lambda t: t.dividends)
    payers = {s: d for s, d in dividends.items() if len(d)}
    print(
        f"\nTicker.dividends: {time.monotonic() - start:.0f}s, ok {len(dividends)}, payers {len(payers)}, errors {dict(errors)}"
    )
    if payers:
        earliest = min(d.index.min() for d in payers.values())
        print(
            "earliest dividend",
            earliest,
            "median events per payer",
            pd.Series([len(d) for d in payers.values()]).median(),
        )

    start = time.monotonic()
    options, errors = per_ticker(symbols, lambda t: t.options)
    listed = [s for s, o in options.items() if o]
    print(
        f"\nTicker.options: {time.monotonic() - start:.0f}s, ok {len(options)}, with options {len(listed)}, errors {dict(errors)}"
    )
    print("without options", [s for s, o in options.items() if not o][:30])

    today = date.today()
    for symbol in ["KO", "O", "JNJ", "PG", "T", "VZ", "XOM", "MO", "MMM", "BEN"]:
        ticker = yf.Ticker(symbol)
        expiry = third_friday_on_or_after(today + timedelta(days=1), ticker.options)
        chain = ticker.option_chain(expiry)
        open_interest = int(
            chain.calls["openInterest"].fillna(0).sum()
            + chain.puts["openInterest"].fillna(0).sum()
        )
        print(f"open interest {symbol} {expiry}: {open_interest}")

    sample = ["KO", "JNJ", "O", "BRK-B", "AAPL"]
    bulk = yf.download(
        sample,
        period="max",
        auto_adjust=False,
        actions=True,
        group_by="ticker",
        progress=False,
    )
    for symbol in sample:
        bulk_events = int((bulk[symbol]["Dividends"].fillna(0) > 0).sum())
        print(
            f"max-period bulk dividends {symbol}: {bulk_events} vs Ticker.dividends {len(dividends.get(symbol, []))}"
        )


main()
