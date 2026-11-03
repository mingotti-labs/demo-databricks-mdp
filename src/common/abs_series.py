# Helpers for the ABS CPI fetch (src/common/fetch_abs.py): one request per series to
# the ABS Data API (no key) and rows from its CSV-with-labels answer. The notebook
# writes the JSON Lines files.
import csv
import io
import json

import requests

DATAFLOW = "ABS,CPI,2.0.0"
SERIES = ["1.10001.10.50.Q", "1.10001.10.50.M"]
LABELS = {
    "Measure": "measure",
    "Index": "index",
    "Adjustment Type": "adjustment_type",
    "Region": "region",
    "Frequency": "frequency",
    "Unit of Measure": "unit",
    "Reference Base Period": "base_period",
}


def get_csv(api_url: str, series_key: str) -> str:
    """GET one series as CSV with labels; a non-200 status names the key and status."""
    response = requests.get(
        f"{api_url}/data/{DATAFLOW}/{series_key}",
        params={"format": "csvfilewithlabels"},
        timeout=120,
    )
    if response.status_code != 200:
        raise RuntimeError(f"ABS {series_key}: HTTP {response.status_code}")
    return response.text


def observation_rows(series_key: str, text: str) -> list[dict]:
    """One row per observation with a value, sorted by period; none at all fails.

    Values and periods stay text as the ABS sent them (`1948-Q3`, `2024-04`).
    `obs_status` is the ABS status code, null when blank.
    """
    rows = [
        {
            "series_key": series_key,
            "time_period": row["TIME_PERIOD"],
            "value": row["OBS_VALUE"],
        }
        | {name: row[label] for label, name in LABELS.items()}
        | {"obs_status": row["OBS_STATUS"] or None}
        for row in csv.DictReader(io.StringIO(text))
        if row["OBS_VALUE"]
    ]
    if not rows:
        raise RuntimeError(f"ABS {series_key}: no rows")
    return sorted(rows, key=lambda row: row["time_period"])


def stamp(rows: list[dict], ingested: str) -> list[dict]:
    """Add the fetch time to every row."""
    return [row | {"ingested_timestamp": ingested} for row in rows]


def to_jsonl(rows: list[dict]) -> str:
    return "".join(json.dumps(row) + "\n" for row in rows)
