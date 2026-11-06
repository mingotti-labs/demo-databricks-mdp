"""Probe P0 (strategies, read only): does Yahoo return full daily history for the candidate bear funds?

Usage: uvx --with yfinance python p0_bear_funds_yahoo.py
"""

import yfinance as yf

FUNDS = ["SQQQ", "PSQ", "SH", "SDS", "SPXU"]

for symbol in FUNDS:
    ticker = yf.Ticker(symbol)
    history = ticker.history(period="max", auto_adjust=False)
    info = ticker.get_info()
    print(symbol, info.get("longName"), info.get("exchange"), info.get("quoteType"),
          "rows", len(history), "first", history.index.min().date(), "last", history.index.max().date(),
          "last close", round(float(history["Close"].iloc[-1]), 2))
