"""P2: which market does each current S&P 500 symbol trade on?

Sources compared: SEC company_tickers_exchange.json (exchange name per ticker)
and Yahoo (yfinance fast_info exchange code). Output: coverage, the exchange
values seen, and where the two disagree once mapped to operating MICs.
Input: p2_symbols.txt (symbol | cik, current Wikipedia list from dev Landing).
"""
import json
from collections import Counter

import requests
import yfinance as yf

UA = {"User-Agent": "mdp handsonessential@gmail.com"}
SEC_TO_MIC = {"Nasdaq": "XNAS", "NYSE": "XNYS", "CBOE": "XCBO", "NYSE Arca": "XNYS", "NYSE American": "XNYS"}  # operating MICs
YAHOO_TO_MIC = {"NMS": "XNAS", "NGM": "XNAS", "NCM": "XNAS", "NYQ": "XNYS", "PCX": "XNYS", "ASE": "XNYS", "BTS": "XCBO"}

lines = open("p2_symbols.txt", encoding="utf-8").read().splitlines()[1:]
members = [tuple(part.strip() for part in line.split("|")) for line in lines if "|" in line]
print("current members", len(members), "distinct symbols", len({s for s, _ in members}))

sec = requests.get("https://www.sec.gov/files/company_tickers_exchange.json", headers=UA, timeout=60).json()
fields = sec["fields"]
sec_rows = [dict(zip(fields, row)) for row in sec["data"]]
print("SEC fields", fields, "rows", len(sec_rows))
sec_by_ticker = {}
for row in sec_rows:
    sec_by_ticker.setdefault(row["ticker"].upper(), []).append(row)

yahoo = {}
for symbol, _ in members:
    ticker = symbol.replace(".", "-")
    try:
        yahoo[symbol] = yf.Ticker(ticker).fast_info["exchange"]
    except Exception as error:
        yahoo[symbol] = f"ERROR {type(error).__name__}"

sec_missing, sec_exchange, yahoo_exchange, disagree, unmapped = [], Counter(), Counter(), [], []
for symbol, cik in members:
    rows = sec_by_ticker.get(symbol.upper()) or sec_by_ticker.get(symbol.replace(".", "-").upper())
    sec_name = rows[0]["exchange"] if rows else None
    if not rows:
        sec_missing.append(symbol)
    sec_exchange[sec_name] += 1
    yahoo_exchange[yahoo[symbol]] += 1
    sec_mic, yahoo_mic = SEC_TO_MIC.get(sec_name), YAHOO_TO_MIC.get(yahoo[symbol])
    if sec_name and not sec_mic or not yahoo_mic:
        unmapped.append((symbol, sec_name, yahoo[symbol]))
    if sec_mic and yahoo_mic and sec_mic != yahoo_mic:
        disagree.append((symbol, sec_name, yahoo[symbol]))

print("SEC exchange values", dict(sec_exchange))
print("SEC missing", len(sec_missing), sec_missing[:20])
print("Yahoo exchange values", dict(yahoo_exchange))
print("unmapped (symbol, sec, yahoo)", len(unmapped), unmapped[:20])
print("disagree", len(disagree), disagree[:30])
