# Databricks notebook source
# Checks the Silver Domain investments tables after a run (openspec
# silver-domain-investments): unique keys, every symbol has a listing and a company,
# one company per symbol, every listing has a known market, recent prices and rates,
# contiguous fundamentals validity ranges, net income coverage and an Australian
# dollar amount on every dividend the held rates reach. Each check lists the
# offenders it finds; the notebook fails with all of them. Run only by run_investments.
import sys

dbutils.widgets.text("catalog", "")
dbutils.widgets.text("workspace_file_path", "")
dbutils.widgets.text("check_symbol", "")
catalog = dbutils.widgets.get("catalog")
check_symbol = dbutils.widgets.get("check_symbol")

sys.path.insert(0, f"{dbutils.widgets.get('workspace_file_path')}/src")
from common.investments import RATES, market_code_sql  # noqa: E402

DOMAIN = f"{catalog}.silver_domain_investments"
LANDING = f"{catalog}.silver_landing"
MIN_NET_INCOME_COVERAGE = 0.95
KEYS = {
    "company": ["company_id"],
    "market": ["market_identifier_code"],
    "listing": ["listing_id"],
    "index_membership": ["listing_id", "valid_from_timestamp"],
    "price_daily": ["listing_id", "trade_date"],
    "dividend": ["listing_id", "ex_dividend_date"],
    "company_fundamentals": ["company_id", "valid_from_date"],
    "market_rate_daily": ["rate_code", "observation_date"],
    "options_activity": ["listing_id"],
}
CURRENT_MEMBERS = f"""
  SELECT l.listing_id, l.trading_symbol_code, l.company_id, l.market_identifier_code
  FROM {DOMAIN}.listing l JOIN {DOMAIN}.index_membership m
    ON m.listing_id = l.listing_id AND m.is_current
"""

# COMMAND ----------


def offenders(sql: str) -> list[str]:
    """First column of the rows a check query returns."""
    return [str(row[0]) for row in spark.sql(sql).limit(10).collect()]


checks = {}
for table, keys in KEYS.items():
    joined = ", ".join(keys)
    checks[f"{table}: key ({joined}) not unique"] = (
        f"SELECT concat_ws(',', {joined}) FROM {DOMAIN}.{table} GROUP BY {joined} HAVING count(*) > 1"
    )

checks["current member has no listing"] = f"""
  SELECT symbol FROM {LANDING}.wikipedia__sp500_constituents w WHERE is_current
  AND NOT EXISTS (SELECT 1 FROM {DOMAIN}.listing l WHERE l.trading_symbol_code = w.symbol)"""
checks["current member's listing has no company"] = f"""
  SELECT m.trading_symbol_code FROM ({CURRENT_MEMBERS}) m
  LEFT JOIN {DOMAIN}.company c ON c.company_id = m.company_id WHERE c.company_id IS NULL"""
for dataset in ("prices", "events", "options"):
    checks[f"yahoo {dataset} symbol has no listing"] = f"""
      SELECT DISTINCT symbol FROM {LANDING}.yahoo__{dataset} y
      WHERE NOT EXISTS (SELECT 1 FROM {DOMAIN}.listing l WHERE l.trading_symbol_code = y.symbol)"""
checks["one symbol maps to more than one central index key"] = f"""
  SELECT symbol FROM {LANDING}.wikipedia__sp500_constituents
  GROUP BY symbol HAVING count(DISTINCT cik) > 1"""
checks["listing has no known market"] = f"""
  SELECT l.trading_symbol_code FROM {DOMAIN}.listing l
  LEFT JOIN {DOMAIN}.market m ON m.market_identifier_code = l.market_identifier_code
  WHERE m.market_identifier_code IS NULL"""
checks["Yahoo exchange code has no market mapping"] = f"""
  SELECT concat_ws(' ', symbol, exchange_code) FROM {LANDING}.yahoo__calendar
  WHERE is_current AND exchange_code IS NOT NULL AND {market_code_sql("exchange_code")} IS NULL"""
checks["current member has no price in the last 7 days"] = f"""
  SELECT m.trading_symbol_code FROM ({CURRENT_MEMBERS}) m
  LEFT JOIN (SELECT listing_id, max(trade_date) AS last_date FROM {DOMAIN}.price_daily
             GROUP BY listing_id) p ON p.listing_id = m.listing_id
  WHERE p.last_date IS NULL OR p.last_date < date_sub(current_date(), 7)"""
checks["fundamentals validity ranges overlap or leave a gap"] = f"""
  SELECT company_id FROM (
    SELECT company_id, valid_to_date,
           lead(valid_from_date) OVER (PARTITION BY company_id ORDER BY valid_from_date) AS next_from
    FROM {DOMAIN}.company_fundamentals)
  WHERE next_from IS NOT NULL AND date_add(valid_to_date, 1) != next_from"""
checks["company does not have exactly one fundamentals row ending 9999-12-31"] = f"""
  SELECT company_id FROM {DOMAIN}.company_fundamentals
  GROUP BY company_id HAVING sum(CASE WHEN valid_to_date = DATE '9999-12-31' THEN 1 ELSE 0 END) != 1"""
checks["dividend since the first held AUD/USD date has no Australian dollar amount"] = f"""
  SELECT concat_ws(' ', trading_symbol_code, CAST(ex_dividend_date AS STRING)) FROM {DOMAIN}.dividend
  WHERE amount_in_australian_dollars IS NULL AND ex_dividend_date >= (
    SELECT min(observation_date) FROM {DOMAIN}.market_rate_daily
    WHERE rate_code = 'australian_dollar_in_us_dollars')"""
checks["rate is missing or its latest date is more than 7 days old"] = f"""
  SELECT r.rate_code FROM (SELECT * FROM VALUES {", ".join(f"('{c}')" for c, _, _, _ in RATES)} AS r(rate_code)) r
  LEFT JOIN (SELECT rate_code, max(observation_date) AS last_date FROM {DOMAIN}.market_rate_daily
             GROUP BY rate_code) d ON d.rate_code = r.rate_code
  WHERE d.last_date IS NULL OR d.last_date < date_sub(current_date(), 7)"""
if check_symbol:
    checks[f"symbol {check_symbol} has no listing"] = f"""
      SELECT '{check_symbol}' WHERE NOT EXISTS (
        SELECT 1 FROM {DOMAIN}.listing WHERE trading_symbol_code = '{check_symbol}')"""

failures = [f"{name}: {found}" for name, sql in checks.items() if (found := offenders(sql))]

# COMMAND ----------

coverage = spark.sql(
    f"""
    SELECT count(*) AS companies, count(f.net_income) AS with_net_income
    FROM (SELECT DISTINCT company_id FROM ({CURRENT_MEMBERS})) m
    LEFT JOIN {DOMAIN}.company_fundamentals f
      ON f.company_id = m.company_id AND f.valid_to_date = DATE '9999-12-31'
    """
).collect()[0]
if coverage.with_net_income < MIN_NET_INCOME_COVERAGE * coverage.companies:
    failures.append(
        f"net income on the current row for {coverage.with_net_income} of "
        f"{coverage.companies} index companies (needs {MIN_NET_INCOME_COVERAGE:.0%})"
    )

assert not failures, "\n".join(failures)
dbutils.notebook.exit(
    f"{len(checks) + 1} checks passed; net income on {coverage.with_net_income} of {coverage.companies}"
)
