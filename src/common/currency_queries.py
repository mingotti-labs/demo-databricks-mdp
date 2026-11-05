"""Dataset queries of the Currency Monitor dashboard (openspec currency-monitor).

Bare gold table names: the dashboard's dataset catalog and schema (`gold_analytics_gateway` of the target's catalog) fill
them in; silver tables carry their schema name. `:as_of_date` is a dashboard date parameter (default today); the day shown
is the latest day with currency rows on or before it. `:currency_code` is the Currency Deep Dive selector. Also the example
SQL of the Genie agent.
"""

from common.currency import (
    BROAD_INDEX_RATE_CODE,
    CURRENCIES,
    DOLLAR_INDEX_SYMBOL,
    MONITOR_CODE,
    STALE_AFTER_MONTHS,
    YEAR_TRADING_DAYS,
    value_code,
)
from common.market_climate_queries import CHART_START

DATASETS: dict[str, tuple[str, str]] = {}
SILVER = "silver_domain_investments"
AS_OF = (
    "asof AS (SELECT max(signal_date) AS day FROM monitor_daily_signal "
    f"WHERE monitor_code = '{MONITOR_CODE}' AND signal_code = 'summary' "
    "AND signal_date <= coalesce(:as_of_date, DATE '9999-12-31'))"
)
CURRENCY_ROWS = "signal_code NOT IN ('summary', 'dollar_index', 'dollar_broad_index')"


def dataset(name: str, title: str, query: str) -> None:
    DATASETS[name] = (title, " ".join(query.split()) + " ")


def currency_values() -> str:
    return ", ".join(f"('{c.code}', '{c.name}', {order})" for order, c in enumerate(CURRENCIES, 1))


def country_rates() -> str:
    return ", ".join(
        f"('{c.code}', '{c.name}', '{c.short_rate_code}', '{c.long_rate_code or '-'}')" for c in CURRENCIES
    )


NAMES = f"names AS (SELECT * FROM VALUES {currency_values()} AS names(currency_code, currency_name, currency_order))"
COUNTRIES = f"countries AS (SELECT * FROM VALUES {country_rates()} AS countries(currency_code, currency_name, short_rate_code, long_rate_code))"

dataset("ds_currency_freshness", "Data dates", f"""
WITH {AS_OF}
SELECT (SELECT day FROM asof) AS currency_date,
  (SELECT max(price_date) FROM {SILVER}.price_indicator_daily WHERE trading_symbol_code = '{DOLLAR_INDEX_SYMBOL}') AS dollar_index_date,
  (SELECT max(observation_date) FROM {SILVER}.market_rate_daily WHERE rate_code = '{BROAD_INDEX_RATE_CODE}') AS broad_index_date,
  (SELECT max(observation_date) FROM {SILVER}.market_rate_daily WHERE rate_code = 'swiss_francs_per_us_dollar') AS exchange_rate_date
""")

dataset("ds_dollar", "The dollar indexes of the day", f"""
WITH {AS_OF}
SELECT s.signal_date, s.signal_code, s.signal_name,
  CASE WHEN s.is_yes THEN 'Strong' ELSE 'Weak' END AS dollar_state, s.band_code AS dollar_band,
  CASE s.signal_code WHEN 'dollar_index' THEN 1 ELSE 2 END AS index_order,
  s.measured_value AS index_level, s.threshold_value AS average_200, s.reason_text
FROM monitor_daily_signal s JOIN asof a ON s.signal_date = a.day
WHERE s.monitor_code = '{MONITOR_CODE}' AND s.signal_code IN ('dollar_index', 'dollar_broad_index') ORDER BY index_order
""")

GRID = f"""
WITH {AS_OF}, {NAMES},
against_usd AS (SELECT upper(s.signal_code) AS currency_code, s.is_yes, s.band_code, s.measured_value, s.threshold_value
  FROM monitor_daily_signal s JOIN asof a ON s.signal_date = a.day
  WHERE s.monitor_code = '{MONITOR_CODE}' AND s.lens_code = 'us_dollar' AND {CURRENCY_ROWS}),
against_aud AS (SELECT upper(s.signal_code) AS currency_code, s.is_yes, s.band_code, s.measured_value, s.threshold_value
  FROM monitor_daily_signal s JOIN asof a ON s.signal_date = a.day
  WHERE s.monitor_code = '{MONITOR_CODE}' AND s.lens_code = 'australian_dollar' AND {CURRENCY_ROWS})
"""
dataset("ds_currency_grid", "Currencies against the US dollar and the Australian dollar", GRID + """
SELECT n.currency_code, n.currency_name,
  u.measured_value AS value_in_usd, u.measured_value / u.threshold_value - 1 AS distance_usd,
  CASE u.is_yes WHEN true THEN 'Gaining' WHEN false THEN 'Losing' ELSE 'Base' END AS against_usd, coalesce(u.band_code, 'blue') AS band_usd,
  a.measured_value AS value_in_aud, a.measured_value / a.threshold_value - 1 AS distance_aud,
  CASE a.is_yes WHEN true THEN 'Gaining' WHEN false THEN 'Losing' ELSE 'Base' END AS against_aud, coalesce(a.band_code, 'blue') AS band_aud
FROM names n LEFT JOIN against_usd u ON u.currency_code = n.currency_code
LEFT JOIN against_aud a ON a.currency_code = n.currency_code ORDER BY n.currency_order
""")

dataset("ds_currency_distance", "Distance from the 200-day average", GRID + """
SELECT n.currency_name, n.currency_order, 'Against the US dollar' AS base_label, u.measured_value / u.threshold_value - 1 AS distance_ratio
FROM names n JOIN against_usd u ON u.currency_code = n.currency_code
UNION ALL
SELECT n.currency_name, n.currency_order, 'Against the Australian dollar', a.measured_value / a.threshold_value - 1
FROM names n JOIN against_aud a ON a.currency_code = n.currency_code ORDER BY currency_order
""")

dataset("ds_dollar_history", "The dollar indexes over time", f"""
SELECT b.indicator_date, d.price_close_adjusted AS dxy_close, d.close_adjusted_two_hundred_day_average_amount AS dxy_average,
  b.rate_value AS broad_value, b.two_hundred_day_average_value AS broad_average
FROM {SILVER}.market_rate_indicator_daily b
LEFT JOIN {SILVER}.price_indicator_daily d ON d.trading_symbol_code = '{DOLLAR_INDEX_SYMBOL}' AND d.price_date = b.indicator_date
WHERE b.rate_code = '{BROAD_INDEX_RATE_CODE}' AND b.indicator_date >= {CHART_START} ORDER BY b.indicator_date
""")

dataset("ds_country_rates", "Interest rates of the main countries", f"""
WITH {AS_OF}, {COUNTRIES},
latest AS (SELECT i.rate_code, i.rate_value, i.observation_date FROM {SILVER}.market_rate_indicator_daily i JOIN asof a ON i.indicator_date = a.day)
SELECT c.currency_name AS country_currency, s.rate_value AS short_term_rate, s.observation_date AS short_term_date,
  CASE WHEN s.observation_date < add_months(a.day, -{STALE_AFTER_MONTHS}) THEN 'Older than {STALE_AFTER_MONTHS} months' END AS short_term_note,
  l.rate_value AS ten_year_yield, l.observation_date AS ten_year_date,
  CASE WHEN c.long_rate_code = '-' THEN 'Not available' WHEN l.observation_date < add_months(a.day, -{STALE_AFTER_MONTHS}) THEN 'Older than {STALE_AFTER_MONTHS} months' END AS ten_year_note
FROM countries c CROSS JOIN asof a LEFT JOIN latest s ON s.rate_code = c.short_rate_code
LEFT JOIN latest l ON l.rate_code = c.long_rate_code
""")

dataset("ds_currency_options", "Currencies", f"""
WITH {NAMES} SELECT currency_code, currency_name FROM names ORDER BY currency_order
""")


def value_series_sql(base: str) -> str:
    return f"concat('currency_value_', lower(:currency_code), '_in_{base}')"


dataset("ds_currency_history", "Value of the chosen currency", f"""
SELECT indicator_date,
  max(CASE WHEN rate_code = {value_series_sql('usd')} THEN rate_value END) AS value_in_usd,
  max(CASE WHEN rate_code = {value_series_sql('usd')} THEN two_hundred_day_average_value END) AS average_in_usd,
  max(CASE WHEN rate_code = {value_series_sql('aud')} THEN rate_value END) AS value_in_aud,
  max(CASE WHEN rate_code = {value_series_sql('aud')} THEN two_hundred_day_average_value END) AS average_in_aud
FROM {SILVER}.market_rate_indicator_daily
WHERE rate_code IN ({value_series_sql('usd')}, {value_series_sql('aud')}) AND indicator_date >= {CHART_START}
GROUP BY indicator_date ORDER BY indicator_date
""")

dataset("ds_currency_rates_history", "Interest rates of the chosen currency's country", f"""
WITH {COUNTRIES}
SELECT i.indicator_date, CASE i.rate_code WHEN c.short_rate_code THEN 'Short-term rate' ELSE '10-year yield' END AS rate_label, i.rate_value
FROM countries c JOIN {SILVER}.market_rate_indicator_daily i ON i.rate_code IN (c.short_rate_code, c.long_rate_code)
WHERE c.currency_code = :currency_code AND i.indicator_date >= {CHART_START} ORDER BY i.indicator_date
""")

dataset("ds_base_options", "Base currencies", """
SELECT * FROM VALUES ('AUD', 'Australian dollar'), ('USD', 'US dollar') AS bases(base_code, base_name)
""")

dataset("ds_yield_ranking", "Countries ranked by short-term rate plus the currency's 12-month change", f"""
WITH {AS_OF}, {COUNTRIES},
series_values AS (SELECT rate_code, indicator_date, rate_value, two_hundred_day_average_value AS average_value,
    lag(rate_value, {YEAR_TRADING_DAYS}) OVER (PARTITION BY rate_code ORDER BY indicator_date) AS year_ago
  FROM {SILVER}.market_rate_indicator_daily WHERE rate_code LIKE concat('currency_value_%_in_', lower(:base_code))),
today AS (SELECT v.* FROM series_values v JOIN asof a ON v.indicator_date = a.day),
latest AS (SELECT i.rate_code, i.rate_value, i.observation_date FROM {SILVER}.market_rate_indicator_daily i JOIN asof a ON i.indicator_date = a.day),
ranked AS (
  SELECT c.currency_code, c.currency_name, s.rate_value AS short_term_rate, s.observation_date AS short_term_date,
    l.rate_value AS ten_year_yield,
    CASE WHEN c.currency_code = upper(:base_code) THEN 0 ELSE (t.rate_value / t.year_ago - 1) * 100 END AS currency_change_12m,
    CASE WHEN c.currency_code = upper(:base_code) THEN 0 ELSE (t.rate_value / t.average_value - 1) * 100 END AS distance_from_average
  FROM countries c LEFT JOIN latest s ON s.rate_code = c.short_rate_code LEFT JOIN latest l ON l.rate_code = c.long_rate_code
  LEFT JOIN today t ON t.rate_code = concat('currency_value_', lower(c.currency_code), '_in_', lower(:base_code))
  WHERE s.rate_value IS NOT NULL AND (c.currency_code = upper(:base_code) OR t.year_ago IS NOT NULL))
SELECT rank() OVER (ORDER BY short_term_rate + currency_change_12m DESC) AS rank_position, currency_name,
  round(short_term_rate, 2) AS short_term_rate, short_term_date, round(ten_year_yield, 2) AS ten_year_yield,
  round(currency_change_12m, 1) AS currency_change_12m, round(distance_from_average, 1) AS distance_from_average,
  round(short_term_rate + currency_change_12m, 1) AS short_plus_12m
FROM ranked ORDER BY rank_position
""")
