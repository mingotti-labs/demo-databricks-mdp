"""P1: can serverless reach each host the dividend portfolio story needs?"""

import time

import requests

HOSTS = [
    "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
    "https://financialmodelingprep.com/stable/",
    "https://www.sec.gov/files/company_tickers.json",
    "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json",
    "https://query1.finance.yahoo.com/v8/finance/chart/KO?range=5d&interval=1d",
    "https://query2.finance.yahoo.com/v8/finance/chart/KO?range=5d&interval=1d",
    "https://www.rba.gov.au/statistics/tables/csv/f11.1-data.csv",
    "https://api.stlouisfed.org/fred/series?series_id=DGS10",
]
HEADERS = {"User-Agent": "mdp handsonessential@gmail.com"}


def main() -> None:
    for url in HOSTS:
        start = time.monotonic()
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            outcome = f"{response.status_code} {len(response.content)} bytes"
        except requests.RequestException as error:
            outcome = f"ERROR {type(error).__name__}: {error}"
        print(f"{url} -> {outcome} in {time.monotonic() - start:.1f}s")


main()
