"""P6b: does yfinance's Ticker.calendar give the next dividend's pay date?"""

import logging
import time
from collections import Counter
from io import StringIO

import pandas as pd
import requests
import yfinance as yf

logging.getLogger("yfinance").setLevel(logging.CRITICAL)
WIKIPEDIA = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
HEADERS = {"User-Agent": "mdp handsonessential@gmail.com"}


def main() -> None:
    html = requests.get(WIKIPEDIA, headers=HEADERS, timeout=30).text
    table = pd.read_html(StringIO(html), attrs={"id": "constituents"}, flavor="lxml")[0]
    symbols = [symbol.replace(".", "-") for symbol in table["Symbol"]]

    start = time.monotonic()
    calendars, errors = {}, Counter()
    for symbol in symbols:
        try:
            calendars[symbol] = yf.Ticker(symbol).calendar
        except Exception as error:  # noqa: BLE001 - the probe counts every failure by type
            errors[f"{type(error).__name__}: {str(error)[:80]}"] += 1
    print(
        f"Ticker.calendar: {time.monotonic() - start:.0f}s, ok {len(calendars)}, errors {dict(errors)}"
    )
    print("keys seen", Counter(k for c in calendars.values() for k in c))
    with_pay = {s: c for s, c in calendars.items() if c.get("Dividend Date")}
    print(
        "with Dividend Date",
        len(with_pay),
        "with Ex-Dividend Date",
        sum(1 for c in calendars.values() if c.get("Ex-Dividend Date")),
    )
    for symbol in ["KO", "JNJ", "O", "AAPL", "MSFT"]:
        c = calendars.get(symbol, {})
        print(symbol, "ex", c.get("Ex-Dividend Date"), "pay", c.get("Dividend Date"))


main()
