"""P4: does the ABS Data API (no key) serve the complete monthly CPI, all groups, Australia?

Reads the CPI dataflow's dimensions, then the monthly all-groups index for Australia
since 2024 as CSV with labels. Run: uv run python references/poc/macro-prices/p4_abs_cpi.py
"""
import csv
import io

import requests

API = "https://data.api.abs.gov.au/rest"
FLOW = "ABS,CPI,2.0.0"

structure = requests.get(
    f"{API}/dataflow/{FLOW.replace(',', '/')}",
    params={"references": "datastructure"},
    headers={"Accept": "application/vnd.sdmx.structure+json"},
    timeout=60,
).json()
dsd = structure["data"]["dataStructures"][0]
print("dimensions:", [d["id"] for d in dsd["dataStructureComponents"]["dimensionList"]["dimensions"]])

response = requests.get(
    f"{API}/data/{FLOW}/all",
    params={"startPeriod": "2024-01", "format": "csvfilewithlabels"},
    timeout=120,
)
print("status", response.status_code, "bytes", len(response.content))
rows = list(csv.DictReader(io.StringIO(response.text)))
print("columns:", list(rows[0].keys()))
picked = [
    r for r in rows
    if r.get("INDEX", "").startswith("10001")
    and r.get("MEASURE", "").startswith("1")
    and r.get("REGION", "").startswith("50")
]
print(f"rows {len(rows)}, all-groups Australia index rows {len(picked)}")
for r in picked[-6:]:
    print(" ", r["TIME_PERIOD"], r["OBS_VALUE"], r.get("TSEST"), r.get("FREQ"))

# The monthly series alone, full history: key MEASURE.INDEX.TSEST.REGION.FREQ
for key in ["1.10001.10.50.M", "1.10001.20.50.M", "1.10001.10.50.Q"]:
    r = requests.get(f"{API}/data/{FLOW}/{key}", params={"format": "csvfilewithlabels"}, timeout=120)
    series = sorted(csv.DictReader(io.StringIO(r.text)), key=lambda s: s["TIME_PERIOD"]) if r.status_code == 200 else []
    if not series:
        print(key, "status", r.status_code, r.text[:80])
        continue
    last = series[-1]
    print(f"{key}: {len(series)} rows {series[0]['TIME_PERIOD']} -> {last['TIME_PERIOD']} "
          f"last {last['OBS_VALUE']} [{last['Adjustment Type']}, {last['Unit of Measure']}, base {last['BASE_PERIOD']}]")
