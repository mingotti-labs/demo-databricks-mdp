"""P4: what does the FMP free plan give for the S&P 500 list and dividend dates?

At most 15 calls. The key is read from the `fmp` secret scope and never printed.
"""

import requests
from databricks.sdk.runtime import dbutils

BASE = "https://financialmodelingprep.com"
KEY = dbutils.secrets.get("fmp", "api_key")
MAX_CALLS = 15
calls = 0

STABLE_TO_V3 = {
    "stable/sp500-constituent": "api/v3/sp500_constituent",
    "stable/historical-sp500-constituent": "api/v3/historical/sp500_constituent",
    "stable/dividends-calendar": "api/v3/stock_dividend_calendar",
}


def get(path: str, **params: str) -> requests.Response:
    """Call FMP once, counting calls against the probe budget."""
    global calls
    calls += 1
    assert calls <= MAX_CALLS, "call budget reached"
    return requests.get(f"{BASE}/{path}", params={**params, "apikey": KEY}, timeout=60)


def report(label: str, response: requests.Response) -> list:
    """Print status, limit headers and the shape of the body; return rows."""
    limits = {k: v for k, v in response.headers.items() if "limit" in k.lower()}
    print(f"\n== {label}: {response.status_code} limits={limits}")
    if response.status_code != 200:
        print(response.text.replace(KEY, "<key>")[:300])
        return []
    rows = response.json()
    rows = rows if isinstance(rows, list) else rows.get("historical", [rows])
    print("rows", len(rows), "fields", list(rows[0]) if rows else None)
    if rows:
        print("first", rows[0])
    return rows


def endpoint(path: str, **params: str) -> list:
    """Try the stable endpoint, then its v3 equivalent once if refused."""
    rows = report(path, get(path, **params))
    if not rows and path in STABLE_TO_V3:
        rows = report(STABLE_TO_V3[path], get(STABLE_TO_V3[path], **params))
    return rows


def dividends(symbol: str) -> None:
    rows = report(f"dividends {symbol}", get("stable/dividends", symbol=symbol))
    if not rows:
        return
    dates = sorted(row["date"] for row in rows)
    print("earliest", dates[0], "latest", dates[-1])
    for field in ("declarationDate", "recordDate", "paymentDate"):
        print(
            field, "filled", sum(1 for row in rows if row.get(field)), "of", len(rows)
        )


def main() -> None:
    constituents = endpoint("stable/sp500-constituent")
    if constituents:
        print(
            "symbols with a dot or dash",
            [
                r["symbol"]
                for r in constituents
                if "." in r["symbol"] or "-" in r["symbol"]
            ],
        )
    endpoint("stable/historical-sp500-constituent")
    for symbol in ("KO", "O", "JNJ", "BRK-B", "AAPL"):
        dividends(symbol)
    calendar = endpoint(
        "stable/dividends-calendar", **{"from": "2026-07-01", "to": "2026-09-28"}
    )
    if calendar:
        print("distinct symbols", len({row["symbol"] for row in calendar}))
        print(
            "paymentDate filled",
            sum(1 for row in calendar if row.get("paymentDate")),
            "of",
            len(calendar),
        )
    print("\ncalls used", calls)


main()
