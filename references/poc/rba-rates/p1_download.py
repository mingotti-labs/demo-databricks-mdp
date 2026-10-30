"""P1: can serverless download the four RBA tables, and does the parser read them?

Expected: HTTP 200 for all four; first dates 03-Jan-2023, 04-Jan-2011,
20-May-2013, 31-Jan-1959; the four named series present.
"""

import sys

import requests

sys.path.insert(0, sys.argv[1])
from rba_tables import TABLES, parse_table

BASE = "https://www.rba.gov.au/statistics/tables/csv"
HEADERS = {"User-Agent": "mdp handsonessential@gmail.com"}
EXPECTED = {
    "F11.1": ("03-Jan-2023", "FXRUSD"),
    "F1": ("04-Jan-2011", "FIRMMCRTD"),
    "F2": ("20-May-2013", "FCMYGBAG10D"),
    "F5": ("31-Jan-1959", "FILRHLBVS"),
}


def main() -> None:
    for table_id, name in TABLES.items():
        response = requests.get(f"{BASE}/{name}", headers=HEADERS, timeout=60)
        print(
            table_id, name, "HTTP", response.status_code, len(response.content), "bytes"
        )
        rows = parse_table(table_id, response.text)
        first_date, series = EXPECTED[table_id]
        print(
            " ",
            len(rows),
            "rows",
            len({r["series_id"] for r in rows}),
            "series; first date",
            rows[0]["observation_date"],
            "(expected",
            first_date + ");",
            series,
            "present:",
            any(r["series_id"] == series for r in rows),
        )


if __name__ == "__main__":
    main()
