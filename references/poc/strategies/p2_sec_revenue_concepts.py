"""Probe P2 (strategies, read only): which SEC revenue concepts do companies report, and how recent is each?

Calls SEC companyfacts for a few companies of different kinds (tech, bank, energy holding company, REIT, a high
price-to-sales name) and prints, per candidate concept, the number of facts and the latest period end.

Usage: uvx --with requests python -I p2_sec_revenue_concepts.py
"""

import requests

USER_AGENT = "mdp handsonessential@gmail.com"
CONCEPTS = [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "SalesRevenueNet",
    "RevenuesNetOfInterestExpense",
    "InterestAndDividendIncomeOperating",
]
COMPANIES = {
    "AAPL": "0000320193",
    "NVDA": "0001045810",
    "PLTR": "0001321655",
    "JPM": "0000019617",
    "XOM (old CIK)": "0000034088",
    "XOM (new CIK)": "0002115436",
    "O (REIT)": "0000726728",
    "BRK.B": "0001067983",
}

for name, cik in COMPANIES.items():
    response = requests.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
                            headers={"User-Agent": USER_AGENT}, timeout=60)
    if response.status_code != 200:
        print(name, "HTTP", response.status_code)
        continue
    gaap = response.json()["facts"].get("us-gaap", {})
    found = []
    for concept in CONCEPTS:
        units = gaap.get(concept, {}).get("units", {}).get("USD", [])
        if units:
            found.append(f"{concept}: {len(units)} facts, latest end {max(u['end'] for u in units)}")
    print(name, "|", " ; ".join(found) or "none of the candidates")
