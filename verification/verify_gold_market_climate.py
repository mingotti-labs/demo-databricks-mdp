# Databricks notebook source
# Checks the gold analytics gateway tables after a run (openspec market-climate-gold): unique keys,
# the valuation of the latest day (members used, a plausible price/earnings ratio, ratios equal market
# value over earnings), a climate row for both lenses on every valuation day, every light following
# its yes count and every yes count equal to the answers, and the latest day's market value close to
# a recomputation by another route. Each check lists the offenders it finds; the notebook fails with all
# of them. Run only by run_investments.
dbutils.widgets.text("catalog", "")
dbutils.widgets.text("workspace_file_path", "")
catalog = dbutils.widgets.get("catalog")

GOLD = f"{catalog}.gold_analytics_gateway"
DOMAIN = f"{catalog}.silver_domain_investments"
MIN_MEMBERS_USED = 480
PLAUSIBLE_RATIO = (20, 60)
MARKET_VALUE_TOLERANCE = 0.01


def offenders(sql: str) -> list[str]:
    """First column of the rows a check query returns."""
    return [str(row[0]) for row in spark.sql(sql).limit(10).collect()]


checks = {}
checks["index_valuation_daily: key (index_code, valuation_date) not unique"] = f"""
  SELECT concat_ws(',', index_code, CAST(valuation_date AS STRING)) FROM {GOLD}.index_valuation_daily
  GROUP BY index_code, valuation_date HAVING count(*) > 1"""
checks["monitor_signal_daily: key (signal_date, monitor_code, lens_code, signal_code) not unique"] = f"""
  SELECT concat_ws(',', CAST(signal_date AS STRING), monitor_code, lens_code, signal_code)
  FROM {GOLD}.monitor_signal_daily
  GROUP BY signal_date, monitor_code, lens_code, signal_code HAVING count(*) > 1"""
checks["latest valuation day: too few members used or an implausible ratio"] = f"""
  SELECT concat('day ', valuation_date, ' used ', members_used_count, ' ratio ',
                price_earnings_ten_year_average_inflation_adjusted_ratio)
  FROM {GOLD}.index_valuation_daily
  WHERE valuation_date = (SELECT max(valuation_date) FROM {GOLD}.index_valuation_daily)
    AND (members_used_count < {MIN_MEMBERS_USED}
         OR price_earnings_ten_year_average_inflation_adjusted_ratio IS NULL
         OR price_earnings_ten_year_average_inflation_adjusted_ratio
            NOT BETWEEN {PLAUSIBLE_RATIO[0]} AND {PLAUSIBLE_RATIO[1]})"""
checks["a ratio differs from market value over earnings"] = f"""
  SELECT CAST(valuation_date AS STRING) FROM {GOLD}.index_valuation_daily
  WHERE (earnings_trailing_twelve_months_amount > 0
         AND abs(price_earnings_trailing_twelve_months_ratio
                 - market_value_amount / earnings_trailing_twelve_months_amount) > 0.001)
     OR (earnings_ten_year_average_amount > 0
         AND abs(price_earnings_ten_year_average_ratio
                 - market_value_amount / earnings_ten_year_average_amount) > 0.001)
     OR (earnings_ten_year_average_inflation_adjusted_amount > 0
         AND abs(price_earnings_ten_year_average_inflation_adjusted_ratio
                 - market_value_amount / earnings_ten_year_average_inflation_adjusted_amount) > 0.001)"""
checks["valuation day without a climate row for both lenses"] = f"""
  SELECT CAST(v.valuation_date AS STRING) FROM {GOLD}.index_valuation_daily v
  LEFT JOIN (SELECT signal_date, count(*) AS lenses FROM {GOLD}.monitor_signal_daily
             WHERE signal_code = 'climate' GROUP BY signal_date) c ON c.signal_date = v.valuation_date
  WHERE coalesce(c.lenses, 0) != 2"""
checks["climate light does not follow its yes count"] = f"""
  SELECT concat_ws(' ', CAST(signal_date AS STRING), lens_code, CAST(yes_count AS STRING), band_code)
  FROM {GOLD}.monitor_signal_daily
  WHERE signal_code = 'climate'
    AND band_code != CASE yes_count WHEN 0 THEN 'green' WHEN 1 THEN 'yellow' ELSE 'red' END"""
checks["climate yes count differs from the yes answers"] = f"""
  SELECT concat_ws(' ', CAST(c.signal_date AS STRING), c.lens_code)
  FROM {GOLD}.monitor_signal_daily c
  JOIN (SELECT signal_date, lens_code, count_if(is_yes) AS answers_yes FROM {GOLD}.monitor_signal_daily
        WHERE signal_code != 'climate' GROUP BY signal_date, lens_code) a
    ON a.signal_date = c.signal_date AND a.lens_code = c.lens_code
  WHERE c.signal_code = 'climate' AND c.yes_count != a.answers_yes"""
checks["latest market value differs from a recomputation"] = f"""
  WITH latest AS (
    SELECT valuation_date, market_value_amount FROM {GOLD}.index_valuation_daily
    WHERE valuation_date = (SELECT max(valuation_date) FROM {GOLD}.index_valuation_daily)),
  members AS (
    SELECT l.company_id, max_by(l.listing_id, v.average_volume) AS listing_id FROM {DOMAIN}.index_membership m
    JOIN {DOMAIN}.listing l ON l.listing_id = m.listing_id
    JOIN (SELECT listing_id, avg(price_volume_count) AS average_volume FROM {DOMAIN}.price_daily
          WHERE price_date > date_sub(current_date(), 90) GROUP BY listing_id) v ON v.listing_id = l.listing_id
    WHERE m.is_current AND l.company_id IS NOT NULL GROUP BY l.company_id),
  recomputed AS (
    SELECT sum(p.price_close * coalesce(f.shares_outstanding_count, f.weighted_average_shares_basic_count)) AS value
    FROM members x
    JOIN (SELECT listing_id, max_by(price_close, price_date) AS price_close FROM {DOMAIN}.price_daily
          GROUP BY listing_id) p ON p.listing_id = x.listing_id
    JOIN {DOMAIN}.company_fundamentals f ON f.company_id = x.company_id AND f.valid_to_date = DATE '9999-12-31'
    WHERE coalesce(f.shares_outstanding_count, f.weighted_average_shares_basic_count) IS NOT NULL
      AND f.net_income IS NOT NULL AND f.earnings_ten_year_average_amount IS NOT NULL
      AND f.earnings_ten_year_average_inflation_adjusted_amount IS NOT NULL)
  SELECT concat('table ', latest.market_value_amount, ' recomputed ', recomputed.value)
  FROM latest CROSS JOIN recomputed
  WHERE abs(latest.market_value_amount - recomputed.value) / recomputed.value > {MARKET_VALUE_TOLERANCE}"""

failures = [f"{name}: {found}" for name, sql in checks.items() if (found := offenders(sql))]
assert not failures, "\n".join(failures)
dbutils.notebook.exit(f"{len(checks)} checks passed")
