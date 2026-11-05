# Databricks notebook source
# Checks the Silver Domain investments tables after a run (openspec
# silver-domain-investments): unique keys, every symbol has a listing and a company,
# one company per symbol, every listing has a known market, recent prices and rates,
# contiguous fundamentals validity ranges, net income coverage and an Australian
# dollar amount on every dividend the held rates reach, and CPI on business days only
# with a changed value only on a row that is not carried forward. Each check lists the
# offenders it finds; the notebook fails with all of them. Run only by run_investments.
import sys

dbutils.widgets.text("catalog", "")
dbutils.widgets.text("workspace_file_path", "")
dbutils.widgets.text("check_symbol", "")
catalog = dbutils.widgets.get("catalog")
check_symbol = dbutils.widgets.get("check_symbol")

sys.path.insert(0, f"{dbutils.widgets.get('workspace_file_path')}/src")
from common.investments import CPI_RATES, RATES, market_code_sql  # noqa: E402

DOMAIN = f"{catalog}.silver_domain_investments"
LANDING = f"{catalog}.silver_landing"
MIN_SHARE_COUNT_COVERAGE = 0.97
MIN_NET_INCOME_COVERAGE = 0.95
KEYS = {
    "company": ["company_id"],
    "market": ["market_code"],
    "listing": ["listing_id"],
    "index_membership": ["listing_id", "valid_from_timestamp"],
    "price_daily": ["listing_id", "price_date"],
    "price_indicator_daily": ["listing_id", "price_date"],
    "dividend": ["listing_id", "ex_dividend_date"],
    "company_fundamentals": ["company_id", "valid_from_date"],
    "market_rate_daily": ["rate_code", "observation_date"],
    "market_rate_indicator_daily": ["rate_code", "indicator_date"],
}
CURRENT_MEMBERS = f"""
  SELECT l.listing_id, l.trading_symbol_code, l.company_id, l.market_code
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
  LEFT JOIN {DOMAIN}.market m ON m.market_code = l.market_code
  WHERE m.market_code IS NULL"""
checks["Yahoo exchange code has no market mapping"] = f"""
  SELECT concat_ws(' ', symbol, exchange_code) FROM {LANDING}.yahoo__calendar
  WHERE is_current AND exchange_code IS NOT NULL AND {market_code_sql("exchange_code")} IS NULL"""
checks["current member has no price in the last 7 days"] = f"""
  SELECT m.trading_symbol_code FROM ({CURRENT_MEMBERS}) m
  LEFT JOIN (SELECT listing_id, max(price_date) AS last_date FROM {DOMAIN}.price_daily
             GROUP BY listing_id) p ON p.listing_id = m.listing_id
  WHERE p.last_date IS NULL OR p.last_date < date_sub(current_date(), 7)"""
checks["membership version is current but does not end 9999-12-31, or the reverse"] = f"""
  SELECT trading_symbol_code FROM {DOMAIN}.index_membership
  WHERE is_current != (valid_to_timestamp = TIMESTAMP '9999-12-31')"""
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
  WHERE dividend_amount_in_australian_dollars IS NULL AND ex_dividend_date >= (
    SELECT min(observation_date) FROM {DOMAIN}.market_rate_daily
    WHERE rate_code = 'australian_dollar_in_us_dollars')"""
checks["rate is missing or its latest date is more than 7 days old"] = f"""
  SELECT r.rate_code FROM (SELECT * FROM VALUES {", ".join(f"('{c}')" for c, *_ in RATES)} AS r(rate_code)) r
  LEFT JOIN (SELECT rate_code, max(observation_date) AS last_date FROM {DOMAIN}.market_rate_daily
             GROUP BY rate_code) d ON d.rate_code = r.rate_code
  WHERE d.last_date IS NULL OR d.last_date < date_sub(current_date(), 7)"""
checks["CPI series has no rows"] = f"""
  SELECT c.rate_code FROM (SELECT * FROM VALUES {", ".join(f"('{c}')" for c, *_ in CPI_RATES)} AS c(rate_code)) c
  LEFT JOIN (SELECT DISTINCT rate_code FROM {DOMAIN}.market_rate_daily) d ON d.rate_code = c.rate_code
  WHERE d.rate_code IS NULL"""
checks["CPI row is on a Saturday or Sunday"] = f"""
  SELECT concat_ws(' ', rate_code, CAST(observation_date AS STRING)) FROM {DOMAIN}.market_rate_daily
  WHERE rate_code IN ({", ".join(f"'{c}'" for c, *_ in CPI_RATES)}) AND dayofweek(observation_date) IN (1, 7)"""
checks["CPI value changes on a row marked as carried forward"] = f"""
  SELECT concat_ws(' ', rate_code, CAST(observation_date AS STRING)) FROM (
    SELECT rate_code, observation_date, rate_value, is_carried_forward,
           lag(rate_value) OVER (PARTITION BY rate_code ORDER BY observation_date) AS previous_value
    FROM {DOMAIN}.market_rate_daily
    WHERE rate_code IN ({", ".join(f"'{c}'" for c, *_ in CPI_RATES)}))
  WHERE is_carried_forward AND rate_value != previous_value"""
checks["^GSPC has no prices before 2000"] = f"""
  SELECT '^GSPC' WHERE NOT EXISTS (
    SELECT 1 FROM {DOMAIN}.price_daily WHERE trading_symbol_code = '^GSPC' AND price_date < DATE '2000-01-01')"""
checks["market_rate_indicator_daily: a series misses a ^GSPC trading day since the series began"] = f"""
  WITH s AS (SELECT rate_code, min(indicator_date) AS first_day, count(*) AS row_count
             FROM {DOMAIN}.market_rate_indicator_daily GROUP BY rate_code)
  SELECT concat(rate_code, ' rows ', row_count) FROM s
  WHERE row_count != (SELECT count(DISTINCT price_date) FROM {DOMAIN}.price_daily
                      WHERE trading_symbol_code = '^GSPC' AND price_date >= s.first_day)"""
checks["market_rate_indicator_daily: real rate differs from the effective rate minus the CPI 12-month change"] = f"""
  SELECT CAST(r.indicator_date AS STRING) FROM {DOMAIN}.market_rate_indicator_daily r
  JOIN {DOMAIN}.market_rate_indicator_daily f ON f.indicator_date = r.indicator_date AND f.rate_code = 'us_federal_funds_effective_rate'
  JOIN {DOMAIN}.market_rate_indicator_daily c ON c.indicator_date = r.indicator_date AND c.rate_code = 'us_cpi_change_twelve_months_percent'
  WHERE r.rate_code = 'us_real_federal_funds_rate' AND abs(r.rate_value - (f.rate_value - c.rate_value)) > 0.000001"""
checks["market_rate_indicator_daily: the latest CPI change is not the ratio of the two latest monthly readings"] = f"""
  WITH r AS (
    SELECT observation_date,
           (rate_value / lag(rate_value) OVER (ORDER BY observation_date) - 1) * 100 AS previous_change
    FROM {DOMAIN}.market_rate_daily
    WHERE rate_code = 'us_cpi_all_items_not_seasonally_adjusted' AND NOT is_carried_forward),
  latest AS (SELECT previous_change FROM r ORDER BY observation_date DESC LIMIT 1)
  SELECT concat('table ', i.rate_value, ' expected ', l.previous_change)
  FROM {DOMAIN}.market_rate_indicator_daily i CROSS JOIN latest l
  WHERE i.rate_code = 'us_cpi_change_previous_reading_percent'
    AND i.indicator_date = (SELECT max(indicator_date) FROM {DOMAIN}.market_rate_indicator_daily)
    AND abs(i.rate_value - l.previous_change) > 0.0001"""
checks["price_indicator_daily: 52-week high below the day's own high, or low above the day's own low"] = f"""
  SELECT concat(p.trading_symbol_code, ' ', CAST(p.price_date AS STRING)) FROM {DOMAIN}.price_indicator_daily p
  JOIN {DOMAIN}.price_daily d ON d.listing_id = p.listing_id AND d.price_date = p.price_date
  WHERE p.price_high_fifty_two_week_amount < d.price_high OR p.price_low_fifty_two_week_amount > d.price_low
  LIMIT 10"""
checks["^GSPC has no 200-day average on its latest day"] = f"""
  SELECT '^GSPC' FROM (
    SELECT max_by(close_adjusted_two_hundred_day_average_amount, price_date) AS average
    FROM {DOMAIN}.price_indicator_daily WHERE trading_symbol_code = '^GSPC')
  WHERE average IS NULL"""
checks["Apple's ten-year average differs from a recomputation (plain, inflation-adjusted, year count)"] = f"""
  WITH r AS (
    SELECT f.* FROM {DOMAIN}.company_fundamentals f JOIN {DOMAIN}.company c ON c.company_id = f.company_id
    WHERE c.company_name = 'Apple Inc.' AND f.valid_to_date = DATE '9999-12-31'),
  y AS (
    SELECT f.period_end_date, max_by(f.net_income, f.valid_from_date) AS net_income
    FROM {DOMAIN}.company_fundamentals f JOIN r ON r.company_id = f.company_id
    WHERE f.form_code LIKE '10-K%' AND f.net_income IS NOT NULL AND f.valid_from_date <= r.valid_from_date
    GROUP BY f.period_end_date ORDER BY f.period_end_date DESC LIMIT 10),
  m AS (
    SELECT date_trunc('MONTH', observation_date) AS month_date, max(rate_value) AS cpi_value
    FROM {DOMAIN}.market_rate_daily WHERE rate_code = 'us_cpi_all_items_not_seasonally_adjusted' GROUP BY 1),
  recomputed AS (
    SELECT count(*) AS year_count, avg(y.net_income) AS plain_average,
           avg(y.net_income * now_m.cpi_value / then_m.cpi_value) AS adjusted_average
    FROM y CROSS JOIN r
    JOIN m now_m ON now_m.month_date = date_trunc('MONTH', r.period_end_date)
    JOIN m then_m ON then_m.month_date = date_trunc('MONTH', y.period_end_date))
  SELECT concat('table ', r.earnings_year_count, ' ', r.earnings_ten_year_average_amount, ' ',
                r.earnings_ten_year_average_inflation_adjusted_amount, ' recomputed ', x.year_count, ' ',
                x.plain_average, ' ', x.adjusted_average)
  FROM r CROSS JOIN recomputed x
  WHERE r.earnings_year_count != x.year_count
     OR abs(r.earnings_ten_year_average_amount - x.plain_average) > 1000000
     OR abs(r.earnings_ten_year_average_inflation_adjusted_amount - x.adjusted_average) > 1000000"""
if check_symbol:
    checks[f"symbol {check_symbol} has no listing"] = f"""
      SELECT '{check_symbol}' WHERE NOT EXISTS (
        SELECT 1 FROM {DOMAIN}.listing WHERE trading_symbol_code = '{check_symbol}')"""

failures = [f"{name}: {found}" for name, sql in checks.items() if (found := offenders(sql))]

# COMMAND ----------

coverage = spark.sql(
    f"""
    SELECT count(*) AS companies, count(f.net_income) AS with_net_income,
           count_if(coalesce(f.shares_outstanding_count, f.weighted_average_shares_basic_count) IS NOT NULL) AS with_share_count
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

if coverage.with_share_count < MIN_SHARE_COUNT_COVERAGE * coverage.companies:
    failures.append(
        f"share count (cover page or weighted average) on the current row for {coverage.with_share_count} of "
        f"{coverage.companies} index companies (needs {MIN_SHARE_COUNT_COVERAGE:.0%})"
    )

assert not failures, "\n".join(failures)
dbutils.notebook.exit(
    f"{len(checks) + 1} checks passed; net income on {coverage.with_net_income}, share count on {coverage.with_share_count} of {coverage.companies}"
)
