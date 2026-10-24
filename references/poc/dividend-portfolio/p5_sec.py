"""P5: do SEC company facts cover the figures the ranking needs?

For 12 companies across sectors, find which us-gaap concept carries each
figure in the latest annual report. At most 10 requests a second.
"""

import time

import requests

HEADERS = {"User-Agent": "mdp handsonessential@gmail.com"}
TICKERS = [
    "AAPL",
    "MSFT",
    "JNJ",
    "KO",
    "PG",
    "XOM",
    "JPM",
    "NEE",
    "O",
    "T",
    "ABBV",
    "CB",
]
FIGURES = {
    "net_income": [
        "NetIncomeLoss",
        "ProfitLoss",
        "NetIncomeLossAvailableToCommonStockholdersBasic",
    ],
    "operating_cash_flow": [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    ],
    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
        "PaymentsForCapitalImprovements",
        "PaymentsToAcquireRealEstate",
    ],
    "dividends_paid": [
        "PaymentsOfDividends",
        "PaymentsOfDividendsCommonStock",
        "PaymentsOfOrdinaryDividends",
    ],
    "long_term_debt": [
        "LongTermDebt",
        "LongTermDebtNoncurrent",
        "LongTermDebtAndCapitalLeaseObligations",
        "SeniorNotes",
        "UnsecuredDebt",
    ],
    "short_term_debt": [
        "LongTermDebtCurrent",
        "DebtCurrent",
        "ShortTermBorrowings",
        "CommercialPaper",
    ],
    "cash": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        "Cash",
    ],
    "operating_income": ["OperatingIncomeLoss"],
    "d_and_a": [
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
        "DepreciationAmortizationAndAccretionNet",
        "Depreciation",
    ],
    "interest_expense": [
        "InterestExpense",
        "InterestExpenseNonoperating",
        "InterestExpenseDebt",
        "InterestPaidNet",
    ],
    "shares_outstanding": [
        "dei:EntityCommonStockSharesOutstanding",
        "CommonStockSharesOutstanding",
    ],
}


def get(url: str) -> requests.Response:
    time.sleep(0.15)
    return requests.get(url, headers=HEADERS, timeout=60)


def latest_annual(facts: dict, concept: str) -> str | None:
    """Return 'FYyyyy' of the latest 10-K value for a concept, or None."""
    taxonomy, name = concept.split(":") if ":" in concept else ("us-gaap", concept)
    units = facts["facts"].get(taxonomy, {}).get(name, {}).get("units", {})
    years = [
        v["fy"]
        for values in units.values()
        for v in values
        if v.get("form") == "10-K" and v.get("fy")
    ]
    return f"FY{max(years)}" if years else None


def main() -> None:
    tickers = get("https://www.sec.gov/files/company_tickers.json").json()
    cik = {row["ticker"]: row["cik_str"] for row in tickers.values()}
    print(
        "company_tickers rows",
        len(tickers),
        "BRK forms",
        [t for t in cik if t.startswith("BRK")],
    )

    missing = {}
    for ticker in TICKERS:
        response = get(
            f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik[ticker]:010d}.json"
        )
        facts = response.json()
        print(f"\n{ticker} ({len(response.content) // 1024} KB)")
        for figure, concepts in FIGURES.items():
            found = [(c, y) for c in concepts if (y := latest_annual(facts, c))]
            print(f"  {figure:20} {found if found else 'NONE'}")
            if not found:
                missing.setdefault(figure, []).append(ticker)
    print("\nfigures with no concept:", missing)

    frame = get(
        "https://data.sec.gov/api/xbrl/frames/us-gaap/PaymentsOfDividends/USD/CY2025.json"
    )
    print(
        "\nframes PaymentsOfDividends CY2025:",
        frame.status_code,
        len(frame.content) // 1024,
        "KB",
    )
    if frame.status_code == 200:
        print("companies", len(frame.json()["data"]))


main()
