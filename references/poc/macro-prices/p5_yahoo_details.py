"""P5: do the new symbols get through fetch_yahoo's steps: bulk prices, events, calendar, options?

Calls yfinance the way src/common/fetch_yahoo.py does (one yf.download for all, then
per symbol actions, calendar, options) and builds rows with common.yahoo_market.
Run: uv run --with yfinance==1.7.0 python references/poc/macro-prices/p5_yahoo_details.py
"""
import sys
from datetime import UTC, date, datetime, timedelta

import yfinance as yf

sys.path.insert(0, "src")
from common.investments import YAHOO_EXCHANGE_TO_MARKET
from common.yahoo_market import calendar_row, event_rows, monthly_expiry, option_row, price_rows

SYMBOLS = ["^TRCCRB", "^SPGSCI", "GC=F", "SI=F", "HG=F", "CL=F", "DBC", "GSG"]
today = datetime.now(UTC).date()

data = yf.download(
    SYMBOLS,
    start=(today - timedelta(days=10)).isoformat(),
    end=(today + timedelta(days=1)).isoformat(),
    auto_adjust=False,
    actions=True,
    group_by="ticker",
    threads=True,
    progress=False,
)
for symbol in SYMBOLS:
    frame = data[symbol].dropna(subset=["Close"])
    prices = price_rows(symbol, frame)
    ticker = yf.Ticker(symbol)
    try:
        events = event_rows(symbol, ticker.actions)
        exchange = ticker.fast_info["exchange"]
        calendar = calendar_row(symbol, ticker.calendar, exchange)
        expiries = ticker.options
        expiry = monthly_expiry(expiries, today)
        chain = ticker.option_chain(expiry) if expiry else None
        option = option_row(symbol, expiries, expiry, chain)
    except Exception as error:
        print(f"{symbol:9} prices {len(prices):3} DETAILS FAILED {type(error).__name__}: {error}")
        continue
    market = YAHOO_EXCHANGE_TO_MARKET.get(calendar["exchange_code"], "UNMAPPED")
    print(
        f"{symbol:9} prices {len(prices):3} events {len(events):4} exchange {calendar['exchange_code']} "
        f"-> {market} has_options {option['has_options']} expiry {option.get('nearest_monthly_expiry')}"
    )
