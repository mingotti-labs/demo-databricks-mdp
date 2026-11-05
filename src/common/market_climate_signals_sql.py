"""SQL of the market climate signals (openspec market-climate-gold): three answers and a result per
lens and day, as rows of the long table `monitor_signal_daily` that every monitoring story shares.

Plain strings so a probe can run the exact query against dev before it goes into a pipeline.
"""

from common.market_climate import (
    FED_MAX_LAG_DAYS,
    FED_WINDOW_MONTHS,
    MONITOR_CODE,
    MONITOR_NAME,
    TREND_FLAT_SLOPE,
    lenses_values_sql,
    lights_values_sql,
)
from common.market_climate_sql import DOMAIN, FED_RATE_CODE


def monitor_signal_query(valuation_source: str = "valuation_daily_index") -> str:
    """Market climate rows. `valuation_source` is the index valuation per day: a table or a parenthesised query."""
    return f"""
    WITH lenses AS (
      SELECT * FROM VALUES {lenses_values_sql()} AS lenses(lens_code, lens_name, expensive_line, cheap_line)
    ), lights AS (
      SELECT * FROM VALUES {lights_values_sql()} AS lights(yes_count, light, action)
    ), trend_days AS (
      SELECT i.price_date AS signal_date, i.price_close_adjusted AS close_value,
             i.close_adjusted_two_hundred_day_average_amount AS average_value,
             i.close_adjusted_two_hundred_day_average_slope_ratio AS slope_value,
             i.ingested_timestamp
      FROM {DOMAIN}.price_indicator_daily i
      WHERE i.trading_symbol_code = '^GSPC' AND i.close_adjusted_two_hundred_day_average_amount IS NOT NULL
    ), fed_series AS (
      SELECT observation_date, rate_value, ingested_timestamp
      FROM {DOMAIN}.market_rate_daily WHERE rate_code = '{FED_RATE_CODE}'
    ), fed_changes AS (
      SELECT observation_date AS change_date, rate_value AS rate_after, rate_before FROM (
        SELECT observation_date, rate_value,
               lag(rate_value) OVER (ORDER BY observation_date) AS rate_before
        FROM fed_series
      ) WHERE rate_before IS NOT NULL AND rate_value <> rate_before
    ), fed_latest AS (
      SELECT signal_date, change_date, rate_before, rate_after FROM (
        SELECT t.signal_date, c.change_date, c.rate_before, c.rate_after,
               row_number() OVER (PARTITION BY t.signal_date ORDER BY c.change_date DESC) AS pick
        FROM trend_days t LEFT JOIN fed_changes c ON c.change_date <= t.signal_date
      ) WHERE pick = 1
    ), fed_days AS (
      SELECT signal_date, target_value, ingested_timestamp, change_date, rate_before, rate_after, is_recent FROM (
        SELECT l.signal_date, f.rate_value AS target_value, f.ingested_timestamp,
               l.change_date, l.rate_before, l.rate_after,
               l.change_date IS NOT NULL AND l.signal_date < add_months(l.change_date, {FED_WINDOW_MONTHS}) AS is_recent,
               row_number() OVER (PARTITION BY l.signal_date ORDER BY f.observation_date DESC) AS pick
        FROM fed_latest l
        JOIN fed_series f
          ON f.observation_date <= l.signal_date AND f.observation_date >= date_sub(l.signal_date, {FED_MAX_LAG_DAYS})
      ) WHERE pick = 1
    ), answers AS (
      SELECT v.valuation_date AS signal_date, n.lens_code, n.lens_name,
             'too_expensive' AS signal_code, 'Too expensive' AS signal_name,
             v.price_earnings_ten_year_average_inflation_adjusted_ratio > n.expensive_line AS is_yes,
             CASE WHEN v.price_earnings_ten_year_average_inflation_adjusted_ratio < n.cheap_line THEN 'green'
                  WHEN v.price_earnings_ten_year_average_inflation_adjusted_ratio <= n.expensive_line THEN 'yellow'
                  ELSE 'red' END AS band_code,
             CAST(v.price_earnings_ten_year_average_inflation_adjusted_ratio AS DECIMAL(18, 6)) AS measured_value,
             CAST(n.expensive_line AS DECIMAL(18, 6)) AS threshold_value,
             concat('The S&P 500 price/earnings ratio on 10-year inflation-adjusted earnings is ',
                    format_number(v.price_earnings_ten_year_average_inflation_adjusted_ratio, 1),
                    CASE WHEN v.price_earnings_ten_year_average_inflation_adjusted_ratio > n.expensive_line
                         THEN ', above ' ELSE ', at or below ' END,
                    n.expensive_line, ' (the line of the ', replace(n.lens_code, '_', ' '), ' lens).') AS reason_text,
             v.ingested_timestamp
      FROM {valuation_source} v CROSS JOIN lenses n
      WHERE v.price_earnings_ten_year_average_inflation_adjusted_ratio IS NOT NULL
      UNION ALL
      SELECT f.signal_date, n.lens_code, n.lens_name, 'fed_in_the_way', 'Fed in the way',
             f.change_date IS NOT NULL AND f.rate_after > f.rate_before AND f.is_recent,
             CASE WHEN f.rate_after > f.rate_before THEN CASE WHEN f.is_recent THEN 'red' ELSE 'yellow' END
                  WHEN f.rate_after < f.rate_before AND f.is_recent THEN 'green'
                  ELSE 'yellow' END,
             CAST(f.target_value AS DECIMAL(18, 6)), CAST(f.rate_before AS DECIMAL(18, 6)),
             CASE WHEN f.change_date IS NULL THEN 'No change of the Fed target rate is known yet.'
                  ELSE concat('The Fed target rate (upper limit) is ', f.target_value, '%; its latest change was ',
                              CASE WHEN f.rate_after > f.rate_before THEN 'a hike' ELSE 'a cut' END, ' from ',
                              f.rate_before, '% on ', CAST(f.change_date AS STRING),
                              CASE WHEN f.is_recent THEN ', less than {FED_WINDOW_MONTHS} months ago.'
                                   ELSE ', {FED_WINDOW_MONTHS} months or more ago.' END) END,
             f.ingested_timestamp
      FROM fed_days f CROSS JOIN lenses n
      UNION ALL
      SELECT t.signal_date, n.lens_code, n.lens_name, 'market_going_up', 'Market going up',
             t.close_value > t.average_value,
             CASE WHEN t.close_value <= t.average_value THEN 'red'
                  WHEN t.slope_value >= {TREND_FLAT_SLOPE} THEN 'green' ELSE 'yellow' END,
             CAST(t.close_value AS DECIMAL(18, 6)), CAST(t.average_value AS DECIMAL(18, 6)),
             concat('The S&P 500 closed at ', format_number(t.close_value, 2),
                    CASE WHEN t.close_value > t.average_value THEN ', above' ELSE ', at or below' END,
                    ' its 200-day average of ', format_number(t.average_value, 2),
                    CASE WHEN t.slope_value IS NULL THEN '.'
                         ELSE concat(' (the average moved ', format_number(t.slope_value * 100, 1),
                                     '% over the last 20 days).') END),
             t.ingested_timestamp
      FROM trend_days t CROSS JOIN lenses n
    ), climate AS (
      SELECT a.signal_date, a.lens_code, a.lens_name, count_if(a.is_yes) AS yes_count,
             min(a.ingested_timestamp) AS ingested_timestamp
      FROM answers a
      GROUP BY a.signal_date, a.lens_code, a.lens_name
      HAVING count(*) = 3
    )
    SELECT signal_date, '{MONITOR_CODE}' AS monitor_code, '{MONITOR_NAME}' AS monitor_name, lens_code, lens_name,
           signal_code, signal_name, is_yes, band_code, measured_value, threshold_value, reason_text,
           CAST(NULL AS BIGINT) AS yes_count, CAST(NULL AS STRING) AS action_name, ingested_timestamp
    FROM answers
    UNION ALL
    SELECT c.signal_date, '{MONITOR_CODE}', '{MONITOR_NAME}', c.lens_code, c.lens_name,
           'climate', c.lens_name, CAST(NULL AS BOOLEAN), g.light,
           CAST(NULL AS DECIMAL(18, 6)), CAST(NULL AS DECIMAL(18, 6)),
           concat(c.lens_name, ' is ', g.light, ' (', g.action, '): ', c.yes_count, ' of 3 answers are yes.'),
           c.yes_count, g.action, c.ingested_timestamp
    FROM climate c JOIN lights g ON g.yes_count = c.yes_count
    """
