"""P6: does yf.download with start 1970-01-01 return each new symbol's full history?

Same call as fetch_yahoo.download (auto_adjust=False, actions=True, group_by ticker),
one symbol at a time as the reload path does. Prints rows, first and last day, and
dividend events. Run: uv run --with yfinance==1.7.0 python references/poc/macro-prices/p6_full_history_download.py
"""
from datetime import UTC, datetime, timedelta

import yfinance as yf

SYMBOLS = ["^TRCCRB", "^SPGSCI", "GC=F", "SI=F", "HG=F", "CL=F", "DBC", "GSG"]
today = datetime.now(UTC).date()

for symbol in SYMBOLS:
    data = yf.download(
        [symbol],
        start="1970-01-01",
        end=(today + timedelta(days=1)).isoformat(),
        auto_adjust=False,
        actions=True,
        group_by="ticker",
        threads=True,
        progress=False,
    )
    frame = data[symbol].dropna(subset=["Close"])
    events = int((frame["Dividends"] > 0).sum())
    print(f"{symbol:9} rows {len(frame):6} {frame.index[0].date()} -> {frame.index[-1].date()} dividends {events}")
