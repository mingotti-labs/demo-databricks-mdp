"""SQL of the inflation/deflation monitor's signal rows (openspec inflation-deflation-monitor): four stars and a
rating per trading day, as rows of the long table `monitor_daily_signal` that every monitoring story shares.

Plain strings so a probe can run the exact query against dev or prd before it goes into a pipeline. `domain` is the
silver schema (with the catalog in a probe); `indicator_source` is the rate indicator table or a parenthesised query.
"""

from common.inflation import (
    COMMODITY_SYMBOL,
    GOLD_SYMBOL,
    LENS_CODE,
    LENS_NAME,
    MAX_LAG_DAYS,
    MONITOR_CODE,
    MONITOR_NAME,
    ratings_values_sql,
)
from common.market_rate_indicator_sql import CPI_RATE_CODE, CPI_TWELVE_CODE, FED_RATE_CODE
from common.market_climate_sql import DOMAIN


def inflation_signal_query(domain: str = DOMAIN, indicator_source: str | None = None) -> str:
    """Inflation/deflation rows. Days without the four inputs get no rows; the daily inputs (rate, prices, CPI index) may be
    at most MAX_LAG_DAYS old, the monthly CPI change is carried until the next reading."""
    indicator_source = indicator_source or f"{domain}.market_rate_indicator_daily"
    return f"""
    WITH ratings AS (
      SELECT * FROM VALUES {ratings_values_sql()} AS ratings(rating, band, label)
    ), rate_days AS (
      SELECT * FROM {indicator_source}
      WHERE rate_code IN ('{CPI_RATE_CODE}', '{FED_RATE_CODE}')
        AND observation_date >= date_sub(indicator_date, {MAX_LAG_DAYS})
    ), days AS (
      SELECT indicator_date AS signal_date FROM rate_days WHERE rate_code = '{FED_RATE_CODE}'
    ), prices AS (
      SELECT d.signal_date, p.trading_symbol_code, p.price_close_adjusted AS close_value,
             p.close_adjusted_two_hundred_day_average_amount AS average_value,
             p.close_adjusted_two_hundred_day_average_slope_ratio AS slope_value, p.ingested_timestamp
      FROM days d
      JOIN {domain}.price_indicator_daily p
        ON p.trading_symbol_code IN ('{COMMODITY_SYMBOL}', '{GOLD_SYMBOL}')
       AND p.price_date <= d.signal_date AND p.price_date >= date_sub(d.signal_date, {MAX_LAG_DAYS})
      WHERE p.close_adjusted_two_hundred_day_average_amount IS NOT NULL
      QUALIFY row_number() OVER (PARTITION BY d.signal_date, p.trading_symbol_code ORDER BY p.price_date DESC) = 1
    ), stars AS (
      SELECT p.signal_date, 'commodity_prices' AS signal_code, 'Commodity prices' AS signal_name,
             p.slope_value > 0 AS is_yes,
             CAST(p.slope_value AS DECIMAL(18, 6)) AS measured_value, CAST(0 AS DECIMAL(18, 6)) AS threshold_value,
             concat('The CRB commodity index closed at ', format_number(p.close_value, 2), '; its 200-day average of ',
                    format_number(p.average_value, 2), ' moved ', format_number(p.slope_value * 100, 1),
                    '% over the last 20 days, so the star is ', CASE WHEN p.slope_value > 0 THEN 'on.' ELSE 'off.' END) AS reason_text,
             p.ingested_timestamp
      FROM prices p WHERE p.trading_symbol_code = '{COMMODITY_SYMBOL}' AND p.slope_value IS NOT NULL
      UNION ALL
      SELECT r.indicator_date, 'consumer_prices', 'Consumer prices',
             r.two_hundred_day_average_change_value > 0,
             r.two_hundred_day_average_change_value, CAST(0 AS DECIMAL(18, 6)),
             concat('The 200-day average of the US consumer price index is ', format_number(r.two_hundred_day_average_value, 2),
                    ' and moved ', format_number(r.two_hundred_day_average_change_value, 2),
                    ' points over the last 20 days, so the star is ',
                    CASE WHEN r.two_hundred_day_average_change_value > 0 THEN 'on.' ELSE 'off.' END),
             r.ingested_timestamp
      FROM rate_days r WHERE r.rate_code = '{CPI_RATE_CODE}' AND r.two_hundred_day_average_change_value IS NOT NULL
      UNION ALL
      SELECT p.signal_date, 'gold_prices', 'Gold prices',
             p.close_value > p.average_value,
             CAST(p.close_value AS DECIMAL(18, 6)), CAST(p.average_value AS DECIMAL(18, 6)),
             concat('Gold closed at ', format_number(p.close_value, 2),
                    CASE WHEN p.close_value > p.average_value THEN ', above' ELSE ', at or below' END,
                    ' its 200-day average of ', format_number(p.average_value, 2), ', so the star is ',
                    CASE WHEN p.close_value > p.average_value THEN 'on.' ELSE 'off.' END),
             p.ingested_timestamp
      FROM prices p WHERE p.trading_symbol_code = '{GOLD_SYMBOL}'
      UNION ALL
      SELECT r.indicator_date, 'interest_rates', 'Interest rates',
             r.rate_value > r.two_hundred_day_average_value,
             r.rate_value, r.two_hundred_day_average_value,
             concat('The federal funds effective rate is ', format_number(r.rate_value, 2),
                    CASE WHEN r.rate_value > r.two_hundred_day_average_value THEN '%, above' ELSE '%, at or below' END,
                    ' its 200-day average of ', format_number(r.two_hundred_day_average_value, 2), '%, so the star is ',
                    CASE WHEN r.rate_value > r.two_hundred_day_average_value THEN 'on.' ELSE 'off.' END),
             r.ingested_timestamp
      FROM rate_days r WHERE r.rate_code = '{FED_RATE_CODE}' AND r.two_hundred_day_average_value IS NOT NULL
    ), scored AS (
      SELECT s.signal_date, count_if(s.is_yes) AS stars_on, min(s.ingested_timestamp) AS ingested_timestamp
      FROM stars s GROUP BY s.signal_date HAVING count(*) = 4
    ), rated AS (
      SELECT c.signal_date, c.stars_on, c.ingested_timestamp, t.rate_value AS twelve_change,
             CASE WHEN c.stars_on = 0 AND t.rate_value < 0 THEN -1 ELSE c.stars_on END AS rating
      FROM scored c JOIN {indicator_source} t ON t.indicator_date = c.signal_date AND t.rate_code = '{CPI_TWELVE_CODE}'
    )
    SELECT s.signal_date, '{MONITOR_CODE}' AS monitor_code, '{MONITOR_NAME}' AS monitor_name,
           '{LENS_CODE}' AS lens_code, '{LENS_NAME}' AS lens_name, s.signal_code, s.signal_name, s.is_yes,
           CASE WHEN s.is_yes THEN 'red' ELSE 'green' END AS band_code, s.measured_value, s.threshold_value, s.reason_text,
           CAST(NULL AS BIGINT) AS yes_count, CAST(NULL AS STRING) AS action_name, s.ingested_timestamp
    FROM stars s JOIN rated c ON c.signal_date = s.signal_date
    UNION ALL
    SELECT r.signal_date, '{MONITOR_CODE}', '{MONITOR_NAME}', '{LENS_CODE}', '{LENS_NAME}',
           'rating', 'Inflation rating', CAST(NULL AS BOOLEAN), g.band,
           CAST(r.rating AS DECIMAL(18, 6)), CAST(r.twelve_change AS DECIMAL(18, 6)),
           concat(g.label, ': ', r.stars_on, ' of 4 indicators point to inflation; US consumer prices changed ',
                  format_number(r.twelve_change, 1), '% over 12 months.'),
           CAST(r.stars_on AS BIGINT), g.label, r.ingested_timestamp
    FROM rated r JOIN ratings g ON g.rating = r.rating
    """
