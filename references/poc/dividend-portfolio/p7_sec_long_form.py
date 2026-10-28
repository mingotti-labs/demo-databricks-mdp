"""P7 (sec-company-facts P1): shape of company facts in long form.

For 20 companies across sectors, flatten companyfacts to one row per reported
value for the mapped concepts only, then report rows per company, missing
values per key column, duplicate keys and the JSON Lines size, and extrapolate
to 505 companies. At most 10 requests a second.
"""

import csv
import io
import json
import time
from collections import Counter

import requests

HEADERS = {"User-Agent": "mdp handsonessential@gmail.com"}
MAPPING_URL = (
    "https://raw.githubusercontent.com/mingotti-labs/demo-databricks-mdp/main/"
    "data/portfolio/concept_mapping.csv"
)
TICKERS = [
    "AAPL", "MSFT", "JNJ", "KO", "PG", "JPM", "BAC", "CB", "AIG", "O",
    "PLD", "SPG", "NEE", "DUK", "T", "VZ", "ABBV", "CAT", "HD", "BRK.B",
]
EXTRA_CIKS = {"XOM_OLD": 34088, "XOM_NEW": 2115436}
KEY = ["cik", "taxonomy", "concept", "unit", "accn", "start", "end", "fp", "form", "frame"]
FIELDS = ["start", "end", "val", "accn", "fy", "fp", "form", "filed", "frame"]


def get(url: str) -> requests.Response:
    time.sleep(0.11)
    return requests.get(url, headers=HEADERS, timeout=60)


def mapped_concepts() -> set[tuple[str, str]]:
    """The (taxonomy, concept) pairs in the committed concept mapping."""
    text = requests.get(MAPPING_URL, timeout=60).text
    return {(r["taxonomy"], r["concept"]) for r in csv.DictReader(io.StringIO(text))}


def flatten(cik: str, facts: dict, concepts: set[tuple[str, str]]) -> list[dict]:
    """One row per reported value of a mapped concept."""
    rows = []
    for taxonomy, items in facts.get("facts", {}).items():
        for concept, body in items.items():
            if (taxonomy, concept) not in concepts:
                continue
            for unit, values in body["units"].items():
                for v in values:
                    row = {"cik": cik, "taxonomy": taxonomy, "concept": concept, "unit": unit}
                    row.update({f: v.get(f) for f in FIELDS})
                    rows.append(row)
    return rows


def main() -> None:
    concepts = mapped_concepts()
    print("mapped concepts", len(concepts))
    tickers = get("https://www.sec.gov/files/company_tickers.json").json()
    cik_of = {r["ticker"]: r["cik_str"] for r in tickers.values()}
    targets = {t: cik_of.get(t.replace(".", "-")) for t in TICKERS} | EXTRA_CIKS

    all_rows, sizes = [], []
    for name, cik in targets.items():
        if cik is None:
            print(f"{name}: no CIK in company_tickers")
            continue
        padded = f"{cik:010d}"
        response = get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{padded}.json")
        if response.status_code != 200:
            print(f"{name} {padded}: HTTP {response.status_code}")
            continue
        rows = flatten(padded, response.json(), concepts)
        size = len("\n".join(json.dumps(r) for r in rows).encode())
        sizes.append(size)
        all_rows.extend(rows)
        print(f"{name} {padded}: {len(response.content) // 1024} KB raw, "
              f"{len(rows)} rows, {size // 1024} KB jsonl")

    print("\ntotal rows", len(all_rows), "companies", len(sizes))
    print("missing per key column:",
          {k: sum(1 for r in all_rows if r[k] in (None, "")) for k in KEY})
    for label, key in [("full key", KEY), ("key without frame", KEY[:-1])]:
        counts = Counter(tuple(r[k] for k in key) for r in all_rows)
        dups = {k: n for k, n in counts.items() if n > 1}
        print(f"{label}: {len(dups)} duplicate keys, {sum(dups.values())} rows")
        for k in list(dups)[:3]:
            same = [r for r in all_rows if tuple(r[c] for c in key) == k]
            print("  e.g.", k, "->", [(r["val"], r["fy"], r["filed"]) for r in same])
    full = Counter(json.dumps(r, sort_keys=True) for r in all_rows)
    print("identical full rows:", sum(n - 1 for n in full.values() if n > 1))
    if sizes:
        per = len(all_rows) / len(sizes)
        print(f"\nper company: {per:.0f} rows, {sum(sizes) / len(sizes) / 1024:.0f} KB; "
              f"505 companies: {per * 505:,.0f} rows, {sum(sizes) / len(sizes) * 505 / 1e6:.0f} MB")


main()
