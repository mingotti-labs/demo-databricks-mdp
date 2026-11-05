"""Dataset queries of the Inflation Deflation dashboard (openspec inflation-deflation-monitor).

Bare gold table names: the dashboard's dataset catalog and schema (`gold_analytics_gateway` of the target's catalog)
fill them in; silver tables carry their schema name. `:as_of_date` is a dashboard date parameter (default today);
the day shown is the latest day with a rating on or before it. Also the example SQL of the Genie agent.
"""

from common.inflation import BENCHMARK_NAMES, COMMODITY_SYMBOL, GOLD_SYMBOL, MONITOR_CODE
from common.inflation_sql import CPI_PREVIOUS_CODE, CPI_RATE_CODE, CPI_TWELVE_CODE, FED_RATE_CODE, REAL_RATE_CODE
from common.market_climate_queries import CHART_START

DATASETS: dict[str, tuple[str, str]] = {}
SILVER = "silver_domain_investments"
AS_OF = (
    "asof AS (SELECT max(signal_date) AS day FROM monitor_daily_signal "
    f"WHERE monitor_code = '{MONITOR_CODE}' AND signal_code = 'rating' "
    "AND signal_date <= coalesce(:as_of_date, DATE '9999-12-31'))"
)
STAR_ORDER = "CASE s.signal_code WHEN 'commodity_prices' THEN 1 WHEN 'consumer_prices' THEN 2 WHEN 'gold_prices' THEN 3 ELSE 4 END"


def dataset(name: str, title: str, query: str) -> None:
    DATASETS[name] = (title, " ".join(query.split()) + " ")


def names_values() -> str:
    return ", ".join(f"('{symbol}', '{name}', {order})" for order, (symbol, name) in enumerate(BENCHMARK_NAMES.items(), 1))


dataset("ds_inflation_freshness", "Data dates", f"""
WITH {AS_OF}
SELECT (SELECT day FROM asof) AS rating_date,
  (SELECT max(price_date) FROM {SILVER}.price_indicator_daily WHERE trading_symbol_code = '{COMMODITY_SYMBOL}') AS crb_price_date,
  (SELECT max(price_date) FROM {SILVER}.price_indicator_daily WHERE trading_symbol_code = '{GOLD_SYMBOL}') AS gold_price_date,
  (SELECT max(observation_date) FROM {SILVER}.market_rate_daily WHERE rate_code = '{FED_RATE_CODE}') AS rate_date,
  (SELECT max(observation_date) FROM {SILVER}.market_rate_daily WHERE rate_code = '{CPI_RATE_CODE}' AND NOT is_carried_forward) AS cpi_reading_date
""")

dataset("ds_rating", "Rating of the day", f"""
WITH {AS_OF}
SELECT s.signal_date AS rating_date, s.yes_count AS stars_on, CAST(s.measured_value AS INT) AS rating,
  s.action_name AS label, s.band_code AS rating_band, s.threshold_value AS cpi_change_twelve_months, s.reason_text
FROM monitor_daily_signal s JOIN asof a ON s.signal_date = a.day
WHERE s.monitor_code = '{MONITOR_CODE}' AND s.signal_code = 'rating'
""")

dataset("ds_stars", "Stars of the day", f"""
WITH {AS_OF}
SELECT s.signal_name, s.signal_code, {STAR_ORDER} AS star_order,
  CASE WHEN s.is_yes THEN 'On' ELSE 'Off' END AS star_state, s.band_code AS star_band,
  s.measured_value, s.threshold_value, s.reason_text
FROM monitor_daily_signal s JOIN asof a ON s.signal_date = a.day
WHERE s.monitor_code = '{MONITOR_CODE}' AND s.signal_code <> 'rating' ORDER BY star_order
""")

dataset("ds_rating_history", "Rating history", f"""
SELECT signal_date, yes_count AS stars_on, CAST(measured_value AS INT) AS rating, action_name AS label
FROM monitor_daily_signal
WHERE monitor_code = '{MONITOR_CODE}' AND signal_code = 'rating' AND signal_date >= {CHART_START} ORDER BY signal_date
""")


def price_history(name: str, title: str, symbol: str) -> None:
    dataset(name, title, f"""
SELECT price_date, price_close_adjusted AS price_close, close_adjusted_two_hundred_day_average_amount AS average_200
FROM {SILVER}.price_indicator_daily WHERE trading_symbol_code = '{symbol}' AND price_date >= {CHART_START} ORDER BY price_date
""")


def rate_history(name: str, title: str, rate_code: str) -> None:
    dataset(name, title, f"""
SELECT indicator_date, rate_value, two_hundred_day_average_value AS average_200
FROM {SILVER}.market_rate_indicator_daily WHERE rate_code = '{rate_code}' AND indicator_date >= {CHART_START} ORDER BY indicator_date
""")


price_history("ds_crb_history", "CRB commodity index", COMMODITY_SYMBOL)
price_history("ds_gold_history", "Gold futures", GOLD_SYMBOL)
rate_history("ds_cpi_history", "US consumer price index", CPI_RATE_CODE)
rate_history("ds_rate_history", "Federal funds effective rate", FED_RATE_CODE)
rate_history("ds_real_rate_history", "Real federal funds rate", REAL_RATE_CODE)

dataset("ds_cpi_changes", "US consumer price changes", f"""
SELECT indicator_date, rate_value AS cpi_change, CASE rate_code WHEN '{CPI_TWELVE_CODE}' THEN 'Over 12 months' ELSE 'Against the previous reading' END AS change_label
FROM {SILVER}.market_rate_indicator_daily WHERE rate_code IN ('{CPI_TWELVE_CODE}', '{CPI_PREVIOUS_CODE}') AND indicator_date >= {CHART_START}
ORDER BY indicator_date
""")

BENCHMARKS = f"""
names AS (SELECT * FROM VALUES {names_values()} AS names(symbol, benchmark_name, benchmark_order))
"""
dataset("ds_commodities", "Commodity benchmarks of the day", f"""
WITH {AS_OF}, {BENCHMARKS},
latest AS (SELECT p.*, row_number() OVER (PARTITION BY p.trading_symbol_code ORDER BY p.price_date DESC) AS pick
  FROM {SILVER}.price_indicator_daily p JOIN asof a ON p.price_date <= a.day AND p.price_date >= date_sub(a.day, 7)
  WHERE p.trading_symbol_code IN (SELECT symbol FROM names))
SELECT n.benchmark_name, n.symbol, l.price_date, l.price_close_adjusted AS price_close,
  l.close_adjusted_two_hundred_day_average_amount AS average_200,
  l.price_close_adjusted / l.close_adjusted_two_hundred_day_average_amount - 1 AS distance_ratio,
  l.close_adjusted_two_hundred_day_average_slope_ratio AS slope_ratio,
  CASE WHEN l.price_close_adjusted > l.close_adjusted_two_hundred_day_average_amount THEN 'Above' ELSE 'Below' END AS position_text,
  CASE WHEN l.close_adjusted_two_hundred_day_average_slope_ratio > 0 THEN 'Rising' ELSE 'Falling' END AS direction_text,
  n.symbol = '{COMMODITY_SYMBOL}' AS is_vote
FROM names n LEFT JOIN latest l ON l.trading_symbol_code = n.symbol AND l.pick = 1 ORDER BY n.benchmark_order
""")

dataset("ds_commodities_history", "Commodity benchmarks against their 200-day average", f"""
WITH {BENCHMARKS}
SELECT p.price_date, n.benchmark_name,
  p.price_close_adjusted / p.close_adjusted_two_hundred_day_average_amount - 1 AS distance_ratio
FROM {SILVER}.price_indicator_daily p JOIN names n ON n.symbol = p.trading_symbol_code
WHERE p.close_adjusted_two_hundred_day_average_amount IS NOT NULL AND p.price_date >= {CHART_START} ORDER BY p.price_date
""")
