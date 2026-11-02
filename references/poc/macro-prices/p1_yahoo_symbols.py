"""P1: which Yahoo symbols give daily gold and commodity prices, and do their exchange codes map to a market?

Prints, per symbol: rows, first and last day, last close, currency, Yahoo's
exchange code and the market it maps to in YAHOO_EXCHANGE_TO_MARKET (or UNMAPPED).
Run: uv run python references/poc/macro-prices/p1_yahoo_symbols.py
"""
import sys

import yfinance as yf

sys.path.insert(0, "src")
from common.investments import YAHOO_EXCHANGE_TO_MARKET

SYMBOLS = {
    "Gold futures COMEX": "GC=F",
    "Gold ETF SPDR": "GLD",
    "Gold ETF iShares": "IAU",
    "Silver futures COMEX": "SI=F",
    "CRB index (guess)": "^CRB",
    "CRB TR index (guess)": "^TRCCRB",
    "Bloomberg Commodity index": "^BCOM",
    "S&P GSCI index": "^SPGSCI",
    "Invesco DB Commodity ETF": "DBC",
    "iShares S&P GSCI ETF": "GSG",
    "Crude oil WTI futures": "CL=F",
    "Copper futures": "HG=F",
}

for name, sym in SYMBOLS.items():
    ticker = yf.Ticker(sym)
    try:
        df = ticker.history(period="max", auto_adjust=False)
        currency = ticker.history_metadata.get("currency")
        exchange = ticker.fast_info["exchange"]
    except Exception as e:
        print(f"{name:28} {sym:9} ERROR {type(e).__name__}: {e}")
        continue
    if df.empty:
        print(f"{name:28} {sym:9} EMPTY exchange {exchange}")
        continue
    market = YAHOO_EXCHANGE_TO_MARKET.get(exchange, "UNMAPPED")
    print(
        f"{name:28} {sym:9} rows {len(df):6} {df.index[0].date()} -> {df.index[-1].date()} "
        f"close {df['Close'].iloc[-1]:10.2f} {currency} exchange {exchange} -> {market}"
    )
