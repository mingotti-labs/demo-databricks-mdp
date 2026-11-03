"""P7: do P4's two ABS CPI series requests work from serverless?

Fetches the quarterly and monthly all-groups Australia index as CSV with labels, as
abs-cpi's fetch will, and prints status, timing, row counts, period range and columns.
Run: uv run python run.py p7_abs_serverless --profile <PROFILE> --deps requests
"""
import csv
import io
import time

import requests

API = "https://data.api.abs.gov.au/rest/data/ABS,CPI,2.0.0"

for key in ["1.10001.10.50.Q", "1.10001.10.50.M"]:
    start = time.time()
    response = requests.get(f"{API}/{key}", params={"format": "csvfilewithlabels"}, timeout=120)
    seconds = time.time() - start
    print(f"{key}: status {response.status_code}, {len(response.content)} bytes, {seconds:.1f}s")
    rows = sorted(csv.DictReader(io.StringIO(response.text)), key=lambda r: r["TIME_PERIOD"])
    print(f"  rows {len(rows)}, {rows[0]['TIME_PERIOD']} -> {rows[-1]['TIME_PERIOD']}, "
          f"last value {rows[-1]['OBS_VALUE']}")
    print("  columns:", list(rows[0].keys()))
    print("  labels:", {c: rows[-1][c] for c in ["Measure", "Index", "Adjustment Type", "Region",
                                                 "Frequency", "Unit of Measure", "Reference Base Period"]})
    print("  empty OBS_VALUE:", sum(1 for r in rows if not r["OBS_VALUE"]))
