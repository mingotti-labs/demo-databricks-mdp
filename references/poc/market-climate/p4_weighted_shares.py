"""Probe P4 (read only, local): does SEC report weighted average basic shares for share-class companies?

Calls SEC's companyconcept API for us-gaap WeightedAverageNumberOfSharesOutstandingBasic and prints
each company's latest 10-K/10-Q fact. Output: p4_result.txt.

Usage: uv run python p4_weighted_shares.py
"""

import json
import time
import urllib.request

COMPANIES = {
    "MA": "0001141391",
    "NKE": "0000320187",
    "UPS": "0001090727",
    "FOXA": "0001754301",
    "HSY": "0000047111",
    "GOOGL": "0001652044",
    "AAPL": "0000320193",
}
URL = "https://data.sec.gov/api/xbrl/companyconcept/CIK{cik}/us-gaap/WeightedAverageNumberOfSharesOutstandingBasic.json"
USER_AGENT = "mdp handsonessential@gmail.com"


def main() -> None:
    for symbol, cik in COMPANIES.items():
        request = urllib.request.Request(URL.format(cik=cik), headers={"User-Agent": USER_AGENT})
        data = json.load(urllib.request.urlopen(request))
        rows = [r for r in data["units"]["shares"] if r.get("form", "").startswith("10-")]
        last = max(rows, key=lambda r: (r["end"], r["filed"]))
        print(
            f"{symbol}: {len(rows)} facts, latest end {last['end']} filed {last['filed']} "
            f"{last['form']} value {last['val']:,}"
        )
        time.sleep(0.2)


if __name__ == "__main__":
    main()
