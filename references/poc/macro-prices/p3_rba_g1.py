"""P3: what does RBA table G1 (consumer price inflation) hold, and does the current RBA parser read it?

Prints the header rows, the series, the date range and date convention, the last rows,
and the result of common.rba_tables.parse on the file.
Run: uv run python references/poc/macro-prices/p3_rba_g1.py
"""
import csv
import io
import sys

import requests

sys.path.insert(0, "src")
from common import rba_tables

URL = "https://www.rba.gov.au/statistics/tables/csv/g1-data.csv"

response = requests.get(URL, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
response.raise_for_status()
text = response.content.decode("utf-8-sig", errors="replace")
rows = list(csv.reader(io.StringIO(text)))
for r in rows[:12]:
    print(r[:6])
data = [r for r in rows if r and r[0][:1].isdigit()]
print(f"data rows {len(data)}: {data[0][0]} -> {data[-1][0]}")
for r in data[-4:]:
    print(r[:6])
try:
    parsed = rba_tables.parse_table("G1", text)
    print(f"parse_table: {len(parsed)} rows, last {parsed[-1]}")
except Exception as e:
    print(f"parse_table FAILED: {type(e).__name__}: {e}")
