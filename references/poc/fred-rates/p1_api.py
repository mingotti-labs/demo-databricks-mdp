"""P1: can serverless call the FRED API with the key from the `fred` secret scope?

Prints the shape of series/observations and series for DGS10. Never prints the
key or a URL that contains it.
"""

import requests

BASE = "https://api.stlouisfed.org/fred"


def get(path: str, **params) -> requests.Response:
    key = dbutils.secrets.get("fred", "api_key")  # noqa: F821
    return requests.get(
        f"{BASE}/{path}",
        params={"api_key": key, "file_type": "json", **params},
        timeout=60,
    )


def main() -> None:
    meta = get("series", series_id="DGS10")
    print("series HTTP", meta.status_code)
    print({k: v for k, v in meta.json()["seriess"][0].items() if k != "notes"})

    full = get("series/observations", series_id="DGS10")
    body = full.json()
    rows = body["observations"]
    print("observations HTTP", full.status_code, "keys", sorted(body))
    print("count", body["count"], "returned", len(rows), "limit", body["limit"])
    print("first", rows[0], "last", rows[-1])
    missing = [r for r in rows if r["value"] == "."]
    print("missing '.' values", len(missing), "example", missing[:1])

    recent = get(
        "series/observations", series_id="DGS10", observation_start="2026-10-01"
    )
    print("since 2026-10-01", len(recent.json()["observations"]), "rows")

    bad = get("series/observations", series_id="NOT_A_SERIES")
    print("unknown series HTTP", bad.status_code, bad.json())


if __name__ == "__main__":
    main()
