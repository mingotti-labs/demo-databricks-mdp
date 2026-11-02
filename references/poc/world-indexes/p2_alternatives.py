"""P2: alternative Yahoo symbols for the exchanges P1 could not serve (Saudi, Thailand,
Russia, Sweden, Argentina), including USD country ETFs as a fallback.
Run: uv run --with yfinance python references/poc/world-indexes/p2_alternatives.py
"""
import warnings

import yfinance as yf

warnings.filterwarnings("ignore")
CANDIDATES = {
    "Saudi": ["TASI.SR", "^TASI", "KSA", "2222.SR"],
    "Thailand": ["^SET", "^SET.BK", "THD"],
    "Russia": ["IMOEX.ME", "^IMOEX", "MOEX.ME", "RSX", "ERUS"],
    "Sweden": ["^OMX", "^OMXSPI", "EWD"],
    "Argentina": ["^MERV", "ARGT"],
}
for name, symbols in CANDIDATES.items():
    for sym in symbols:
        df = yf.Ticker(sym).history(period="max", auto_adjust=False)
        if df.empty:
            print(f"{name:10} {sym:10} EMPTY")
            continue
        print(f"{name:10} {sym:10} rows {len(df):6} {df.index[0].date()} -> {df.index[-1].date()} close {df['Close'].iloc[-1]:.2f}")
