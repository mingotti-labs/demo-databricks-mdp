# Helpers for the FRED fetch (src/common/fetch_fred.py): one request to the FRED
# API that never lets the API key reach a log, rows from the `series` and
# `series/observations` payloads, and which observations to request. The notebook
# writes the JSON Lines files.
import json
from datetime import date, timedelta

import requests

SERIES = ["DGS10", "DFF", "DFEDTARU", "DFEDTARL"]
LOOKBACK_DAYS = 31
MISSING = "."


def get_json(api_url: str, key: str, path: str, series_id: str, **params) -> dict:
    """GET `api_url/path` and return its JSON; any failure names the path, series and status.

    The key travels in the query string, and `requests` puts the whole URL into
    its exceptions, so every failure is re-raised without the original exception
    or the URL.
    """
    try:
        response = requests.get(
            f"{api_url}/{path}",
            params={
                "api_key": key,
                "file_type": "json",
                "series_id": series_id,
                **params,
            },
            timeout=60,
        )
    except requests.RequestException as error:
        raise RuntimeError(f"FRED {path} {series_id}: {type(error).__name__}") from None
    if response.status_code != 200:
        try:
            message = response.json().get("error_message", "")
        except ValueError:
            message = ""
        raise RuntimeError(
            f"FRED {path} {series_id}: HTTP {response.status_code} {message}"
        )
    return response.json()


def series_info(payload: dict) -> dict:
    """Title, units and frequency from a `series` payload."""
    series = payload["seriess"][0]
    return {key: series[key] for key in ("title", "units", "frequency")}


def observation_rows(series_id: str, info: dict, payload: dict) -> list[dict]:
    """One row per observation with a value; FRED's `.` (no data) is skipped.

    Values and dates stay text as FRED sent them. `realtime_start` and
    `realtime_end` echo the request day, so they are left out.
    """
    return [
        {
            "series_id": series_id,
            "observation_date": observation["date"],
            "value": observation["value"],
        }
        | info
        for observation in payload["observations"]
        if observation["value"] != MISSING
    ]


def first_day(last_stored: date | None, reload: bool) -> date | None:
    """First observation date to request: LOOKBACK_DAYS before the last stored one.

    None requests everything, for a series with no stored rows or a reload.
    """
    if reload or last_stored is None:
        return None
    return last_stored - timedelta(days=LOOKBACK_DAYS)


def stamp(rows: list[dict], ingested: str) -> list[dict]:
    """Add the fetch time to every row."""
    return [row | {"ingested_timestamp": ingested} for row in rows]


def to_jsonl(rows: list[dict]) -> str:
    return "".join(json.dumps(row) + "\n" for row in rows)
