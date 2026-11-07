"""Probe P7 (strategies, read only): which revenue-like concepts does Camden (CPT, CIK 0000906345) report?

Usage: uvx --with requests python -I p7_cpt_concepts.py
"""

import requests

response = requests.get("https://data.sec.gov/api/xbrl/companyfacts/CIK0000906345.json",
                        headers={"User-Agent": "mdp handsonessential@gmail.com"}, timeout=60)
gaap = response.json()["facts"]["us-gaap"]
for concept, body in sorted(gaap.items()):
    if any(word in concept for word in ("Revenue", "RentalIncome", "LeaseIncome", "SalesRevenue")):
        facts = [f for f in body["units"].get("USD", []) if f.get("fp") == "FY" and f.get("form") == "10-K"]
        if facts:
            latest = max(facts, key=lambda f: f["end"])
            print(f"{concept}: latest 10-K {latest['end']} value {latest['val']:,}")
