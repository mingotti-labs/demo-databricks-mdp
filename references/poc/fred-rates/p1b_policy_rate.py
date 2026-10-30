"""P1b: which FRED series is the Fed's policy rate, and how does it differ from DGS10?

Prints each series' title, frequency and its last three observations. Never
prints the key or a URL that contains it.
"""

import requests

BASE = "https://api.stlouisfed.org/fred"
SERIES = ["DGS10", "DFF", "DFEDTARU", "DFEDTARL", "FEDFUNDS"]


def get(path: str, **params) -> dict:
    key = dbutils.secrets.get("fred", "api_key")  # noqa: F821
    response = requests.get(
        f"{BASE}/{path}",
        params={"api_key": key, "file_type": "json", **params},
        timeout=60,
    )
    return response.json()


def main() -> None:
    for series_id in SERIES:
        meta = get("series", series_id=series_id)["seriess"][0]
        rows = get(
            "series/observations",
            series_id=series_id,
            sort_order="desc",
            limit=3,
        )["observations"]
        print(series_id, "|", meta["title"], "|", meta["frequency"], "|", meta["units"])
        print(
            "   from",
            meta["observation_start"],
            "last",
            [(r["date"], r["value"]) for r in rows],
        )


if __name__ == "__main__":
    main()
