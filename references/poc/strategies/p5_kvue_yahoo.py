"""Probe P5 (strategies, read only): does Yahoo still return recent prices for KVUE (dev verification failed on it)?

Usage: uvx --with yfinance python -I p5_kvue_yahoo.py
"""

import yfinance as yf

history = yf.Ticker("KVUE").history(period="1mo", auto_adjust=False)
print("rows", len(history), "last", history.index.max() if len(history) else None)
print(history.tail(3)[["Close", "Volume"]])
