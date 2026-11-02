"""P1: does Yahoo serve a price-index series for each major exchange?

Prints, per symbol: rows, first and last day, last close, currency, and the
number of days without volume. Run: uv run python references/poc/world-indexes/p1_symbols.py
"""
import yfinance as yf

SYMBOLS = {
    "NYSE/Nasdaq": "^GSPC", "Nasdaq": "^IXIC", "Shanghai": "000001.SS",
    "Shenzhen": "399001.SZ", "Hong Kong": "^HSI", "Tokyo": "^N225",
    "India NSE": "^NSEI", "India BSE": "^BSESN", "Euronext Paris": "^FCHI",
    "Euronext Amsterdam": "^AEX", "Euronext Brussels": "^BFX", "Euronext Lisbon": "PSI20.LS",
    "Euronext Amsterdam/Paris area": "^STOXX50E", "London": "^FTSE",
    "Frankfurt": "^GDAXI", "Toronto": "^GSPTSE", "Switzerland": "^SSMI",
    "Korea": "^KS11", "Taiwan": "^TWII", "Australia": "^AXJO", "Saudi": "^TASI.SR",
    "Brazil": "^BVSP", "Italy": "FTSEMIB.MI", "Spain": "^IBEX", "Mexico": "^MXX",
    "Indonesia": "^JKSE", "South Africa": "^J203.JO", "Turkey": "XU100.IS",
    "Argentina": "^MERV", "Russia": "IMOEX.ME", "New Zealand": "^NZ50",
    "Sweden": "^OMXS30", "Singapore": "^STI", "Thailand": "^SET.BK",
    "Malaysia": "^KLSE", "Israel": "^TA125.TA",
}

for name, sym in SYMBOLS.items():
    try:
        df = yf.Ticker(sym).history(period="max", auto_adjust=False)
        cur = yf.Ticker(sym).history_metadata.get("currency")
    except Exception as e:
        print(f"{name:28} {sym:12} ERROR {type(e).__name__}")
        continue
    if df.empty:
        print(f"{name:28} {sym:12} EMPTY")
        continue
    nov = int((df["Volume"] == 0).sum())
    print(f"{name:28} {sym:12} rows {len(df):6} {df.index[0].date()} -> {df.index[-1].date()} close {df['Close'].iloc[-1]:12.2f} {cur} novol {nov}")
