"""P4b: is the FMP dividends calendar free without a date range? One call."""

import requests
from databricks.sdk.runtime import dbutils

KEY = dbutils.secrets.get("fmp", "api_key")

response = requests.get(
    "https://financialmodelingprep.com/stable/dividends-calendar",
    params={"apikey": KEY},
    timeout=60,
)
print("status", response.status_code)
if response.status_code != 200:
    print(response.text.replace(KEY, "<key>")[:300])
else:
    rows = response.json()
    dates = sorted(row["date"] for row in rows)
    print("rows", len(rows), "distinct symbols", len({row["symbol"] for row in rows}))
    print("dates", dates[0], "to", dates[-1])
    print("paymentDate filled", sum(1 for row in rows if row.get("paymentDate")))
    print("sample symbols", sorted({row["symbol"] for row in rows})[:40])
