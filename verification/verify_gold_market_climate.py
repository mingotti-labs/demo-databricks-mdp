# Databricks notebook source
# Checks the gold analytics gateway tables after a run (openspec market-climate-gold, market-climate-dashboard):
# unique keys, a member row for every member and day, the member rows adding up to the index row,
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
checks["valuation_daily_index: key (index_code, valuation_date) not unique"] = f"""
  SELECT concat_ws(',', index_code, CAST(valuation_date AS STRING)) FROM {GOLD}.valuation_daily_index
  GROUP BY index_code, valuation_date HAVING count(*) > 1"""
checks["monitor_daily_signal: key (signal_date, monitor_code, lens_code, signal_code) not unique"] = f"""
  SELECT concat_ws(',', CAST(signal_date AS STRING), monitor_code, lens_code, signal_code)
  FROM {GOLD}.monitor_daily_signal
  GROUP BY signal_date, monitor_code, lens_code, signal_code HAVING count(*) > 1"""
checks["valuation_daily_index_member: key (index_code, valuation_date, company_id) not unique"] = f"""
  SELECT concat_ws(',', index_code, CAST(valuation_date AS STRING), company_id) FROM {GOLD}.valuation_daily_index_member
  GROUP BY index_code, valuation_date, company_id HAVING count(*) > 1"""
checks["a valuation day without a row for every member"] = f"""
  SELECT concat('day ', CAST(valuation_date AS STRING), ' rows ', count(*)) FROM {GOLD}.valuation_daily_index_member
  GROUP BY valuation_date HAVING count(*) != (SELECT count(DISTINCT company_id) FROM {GOLD}.valuation_daily_index_member)"""
checks["member rows differ from the index row"] = f"""
  SELECT CAST(i.valuation_date AS STRING) FROM {GOLD}.valuation_daily_index i
  JOIN (SELECT valuation_date, count(*) AS member_count, count_if(is_used) AS used_count,
               CAST(sum(CASE WHEN is_used THEN market_value_amount END) AS DECIMAL(34, 2)) AS market_value_amount,
               CAST(sum(CASE WHEN is_used THEN earnings_ten_year_average_inflation_adjusted_amount END)
                    AS DECIMAL(34, 2)) AS earnings_amount
        FROM {GOLD}.valuation_daily_index_member GROUP BY valuation_date) m ON m.valuation_date = i.valuation_date
  WHERE m.member_count != i.member_count OR m.used_count != i.members_used_count
     OR m.market_value_amount != i.market_value_amount
     OR m.earnings_amount != i.earnings_ten_year_average_inflation_adjusted_amount"""
checks["the latest top member's without ratio does not recompute"] = f"""
  WITH day AS (SELECT * FROM {GOLD}.valuation_daily_index_member
               WHERE is_used AND valuation_date = (SELECT max(valuation_date) FROM {GOLD}.valuation_daily_index_member)),
  top AS (SELECT * FROM day ORDER BY price_earnings_effect_ratio DESC LIMIT 1),
  totals AS (SELECT sum(market_value_amount) AS value, sum(earnings_ten_year_average_inflation_adjusted_amount) AS earnings FROM day)
  SELECT concat('table ', top.price_earnings_without_member_ratio, ' recomputed ',
                (totals.value - top.market_value_amount) / (totals.earnings - top.earnings_ten_year_average_inflation_adjusted_amount))
  FROM top CROSS JOIN totals
  WHERE abs(top.price_earnings_without_member_ratio
            - (totals.value - top.market_value_amount) / (totals.earnings - top.earnings_ten_year_average_inflation_adjusted_amount)) > 0.001"""
checks["latest valuation day: too few members used or an implausible ratio"] = f"""
  SELECT concat('day ', valuation_date, ' used ', members_used_count, ' ratio ',
                price_earnings_ten_year_average_inflation_adjusted_ratio)
  FROM {GOLD}.valuation_daily_index
  WHERE valuation_date = (SELECT max(valuation_date) FROM {GOLD}.valuation_daily_index)
    AND (members_used_count < {MIN_MEMBERS_USED}
         OR price_earnings_ten_year_average_inflation_adjusted_ratio IS NULL
         OR price_earnings_ten_year_average_inflation_adjusted_ratio
            NOT BETWEEN {PLAUSIBLE_RATIO[0]} AND {PLAUSIBLE_RATIO[1]})"""
checks["a ratio differs from market value over earnings"] = f"""
  SELECT CAST(valuation_date AS STRING) FROM {GOLD}.valuation_daily_index
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
  SELECT CAST(v.valuation_date AS STRING) FROM {GOLD}.valuation_daily_index v
  LEFT JOIN (SELECT signal_date, count(*) AS lenses FROM {GOLD}.monitor_daily_signal
             WHERE signal_code = 'climate' GROUP BY signal_date) c ON c.signal_date = v.valuation_date
  WHERE coalesce(c.lenses, 0) != 2"""
checks["climate light does not follow its yes count"] = f"""
  SELECT concat_ws(' ', CAST(signal_date AS STRING), lens_code, CAST(yes_count AS STRING), band_code)
  FROM {GOLD}.monitor_daily_signal
  WHERE signal_code = 'climate'
    AND band_code != CASE yes_count WHEN 0 THEN 'green' WHEN 1 THEN 'yellow' ELSE 'red' END"""
checks["climate yes count differs from the yes answers"] = f"""
  SELECT concat_ws(' ', CAST(c.signal_date AS STRING), c.lens_code)
  FROM {GOLD}.monitor_daily_signal c
  JOIN (SELECT signal_date, lens_code, count_if(is_yes) AS answers_yes FROM {GOLD}.monitor_daily_signal
        WHERE signal_code != 'climate' GROUP BY signal_date, lens_code) a
    ON a.signal_date = c.signal_date AND a.lens_code = c.lens_code
  WHERE c.signal_code = 'climate' AND c.yes_count != a.answers_yes"""
checks["latest market value differs from a recomputation"] = f"""
  WITH latest AS (
    SELECT valuation_date, market_value_amount FROM {GOLD}.valuation_daily_index
    WHERE valuation_date = (SELECT max(valuation_date) FROM {GOLD}.valuation_daily_index)),
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

checks["inflation_deflation: a day without exactly four stars and a rating"] = f"""
  SELECT concat(CAST(signal_date AS STRING), ' rows ', count(*)) FROM {GOLD}.monitor_daily_signal
  WHERE monitor_code = 'inflation_deflation' GROUP BY signal_date HAVING count(*) != 5"""
checks["inflation_deflation: a rating that is not the stars on, or -1 without prices below a year ago"] = f"""
  SELECT CAST(r.signal_date AS STRING) FROM {GOLD}.monitor_daily_signal r
  JOIN (SELECT signal_date, count_if(is_yes) AS stars_on FROM {GOLD}.monitor_daily_signal
        WHERE monitor_code = 'inflation_deflation' AND signal_code != 'rating' GROUP BY signal_date) s
    ON s.signal_date = r.signal_date
  WHERE r.monitor_code = 'inflation_deflation' AND r.signal_code = 'rating'
    AND (r.yes_count != s.stars_on
         OR r.measured_value != CASE WHEN s.stars_on = 0 AND r.threshold_value < 0 THEN -1 ELSE s.stars_on END)"""
checks["inflation_deflation: no rating on the latest market climate day"] = f"""
  SELECT 'latest climate day ' || CAST(max(signal_date) AS STRING) FROM {GOLD}.monitor_daily_signal
  WHERE monitor_code = 'market_climate'
  HAVING max(signal_date) > (SELECT coalesce(max(signal_date), DATE '1900-01-01') FROM {GOLD}.monitor_daily_signal
                             WHERE monitor_code = 'inflation_deflation') + 7"""

checks["currency: a summary row that differs from the currency rows it counts"] = f"""
  SELECT concat(CAST(m.signal_date AS STRING), ' ', m.lens_code) FROM {GOLD}.monitor_daily_signal m
  JOIN (SELECT signal_date, lens_code, count_if(is_yes) AS gaining
        FROM {GOLD}.monitor_daily_signal
        WHERE monitor_code = 'currency' AND signal_code NOT IN ('summary', 'dollar_index', 'dollar_broad_index')
        GROUP BY signal_date, lens_code) c ON c.signal_date = m.signal_date AND c.lens_code = m.lens_code
  WHERE m.monitor_code = 'currency' AND m.signal_code = 'summary' AND m.yes_count != c.gaining"""
checks["currency: the latest day does not have 9 currencies and a summary per lens, and both dollar indexes"] = f"""
  WITH latest AS (SELECT max(signal_date) AS day FROM {GOLD}.monitor_daily_signal WHERE monitor_code = 'currency')
  SELECT concat(lens_code, ' currencies ', currencies, ' summary ', summaries, ' indexes ', indexes) FROM (
    SELECT s.lens_code,
           count_if(s.signal_code NOT IN ('summary', 'dollar_index', 'dollar_broad_index')) AS currencies,
           count_if(s.signal_code = 'summary') AS summaries,
           count_if(s.signal_code IN ('dollar_index', 'dollar_broad_index')) AS indexes
    FROM {GOLD}.monitor_daily_signal s JOIN latest l ON s.signal_date = l.day
    WHERE s.monitor_code = 'currency' GROUP BY s.lens_code)
  WHERE currencies != 9 OR summaries != 1 OR indexes != CASE lens_code WHEN 'us_dollar' THEN 2 ELSE 0 END"""
checks["currency: a currency row whose answer does not follow its value and average"] = f"""
  SELECT concat(CAST(signal_date AS STRING), ' ', lens_code, ' ', signal_code) FROM {GOLD}.monitor_daily_signal
  WHERE monitor_code = 'currency' AND signal_code != 'summary' AND is_yes != (measured_value > threshold_value)
    AND abs(measured_value - threshold_value) > 0.00001
  LIMIT 10"""

failures = [f"{name}: {found}" for name, sql in checks.items() if (found := offenders(sql))]
assert not failures, "\n".join(failures)
dbutils.notebook.exit(f"{len(checks)} checks passed")
