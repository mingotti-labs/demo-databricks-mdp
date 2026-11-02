"""P2: what do the FRED US CPI series hold: frequency, date convention, range, last values?

Uses FRED's public graph CSV (no API key); the API serves the same observations.
Run: uv run python references/poc/macro-prices/p2_fred_cpi.py
"""
import csv
import io

import requests

SERIES = ["CPIAUCSL", "CPIAUCNS", "CPILFESL"]

for series_id in SERIES:
    response = requests.get(
        "https://fred.stlouisfed.org/graph/fredgraph.csv", params={"id": series_id}, timeout=60
    )
    response.raise_for_status()
    rows = list(csv.reader(io.StringIO(response.text)))
    header, data = rows[0], rows[1:]
    days = sorted({r[0][8:] for r in data})
    print(f"{series_id}: header {header}, rows {len(data)}, {data[0][0]} -> {data[-1][0]}, days of month {days}")
    for r in data[-3:]:
        print(f"  {r[0]} {r[1]}")
