"""P1: how often do the new concepts appear in a recent 10-K, per current CIK?

For every current S&P 500 CIK (p2_symbols.txt, symbol | cik), fetch SEC company
facts and note which new concepts have a USD or USD/shares fact from a 10-K whose
period ends in the last 18 months. Answers how often the liabilities fallback is
needed and whether preferred_stock is worth keeping.
Run from this folder: uv run --with requests python p1_coverage.py
"""
import time
from collections import Counter
from datetime import date, timedelta

import requests

UA = {"User-Agent": "mdp handsonessential@gmail.com"}
CONCEPTS = [
    "AssetsCurrent",
    "Liabilities",
    "LiabilitiesAndStockholdersEquity",
    "StockholdersEquity",
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    "PreferredStockValue",
    "EarningsPerShareDiluted",
    "EarningsPerShareBasic",
]
CUTOFF = (date.today() - timedelta(days=548)).isoformat()

lines = open("p2_symbols.txt", encoding="utf-8").read().splitlines()[1:]
ciks = sorted({line.split("|")[1].strip().zfill(10) for line in lines if "|" in line})
print("current CIKs", len(ciks), "cutoff", CUTOFF)


def recent_concepts(cik: str) -> set[str] | None:
    """Concepts with a recent 10-K fact, or None when SEC has no facts."""
    response = requests.get(
        f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", headers=UA, timeout=60
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    facts = response.json().get("facts", {}).get("us-gaap", {})
    found = set()
    for concept in CONCEPTS:
        for units in facts.get(concept, {}).get("units", {}).values():
            if any(f["form"].startswith("10-K") and f["end"] >= CUTOFF for f in units):
                found.add(concept)
    return found


per_cik = {}
for index, cik in enumerate(ciks):
    per_cik[cik] = recent_concepts(cik)
    time.sleep(0.12)
    if index % 100 == 0:
        print("fetched", index, flush=True)

with_facts = {cik: found for cik, found in per_cik.items() if found is not None}
print("CIKs with facts", len(with_facts), "without", len(per_cik) - len(with_facts))
counts = Counter(concept for found in with_facts.values() for concept in found)
for concept in CONCEPTS:
    print(f"{concept}: {counts[concept]} of {len(with_facts)}")

no_liabilities = [cik for cik, found in with_facts.items() if "Liabilities" not in found]
fallback_ok = [
    cik
    for cik in no_liabilities
    if "LiabilitiesAndStockholdersEquity" in with_facts[cik]
    and {"StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"}
    & with_facts[cik]
]
print("no Liabilities in a recent 10-K:", len(no_liabilities))
print("  of those the fallback inputs exist:", len(fallback_ok))
print("  no figure at all (no balance sheet total):", len(no_liabilities) - len(fallback_ok))
no_current = [cik for cik, found in with_facts.items() if "AssetsCurrent" not in found]
print("no AssetsCurrent (banks, insurers, others):", len(no_current))
no_eps = [cik for cik, found in with_facts.items() if not {"EarningsPerShareDiluted", "EarningsPerShareBasic"} & found]
print("no earnings per share (either):", len(no_eps))
