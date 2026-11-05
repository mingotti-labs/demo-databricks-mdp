"""SQL of the Currency Monitor's signal rows (openspec currency-monitor): per trading day, the dollar indexes and each
main currency gaining or losing against the US dollar and against the Australian dollar, as rows of the long table
`monitor_daily_signal` that every monitoring story shares.

Plain strings so a probe can run the exact query against dev or prd before it goes into a pipeline. `domain` is the
silver schema (with the catalog in a probe); `indicator_source` is the rate indicator table or a parenthesised query.
"""

from common.currency import (
    BROAD_INDEX_RATE_CODE,
    DOLLAR_INDEX_SYMBOL,
    MAX_VALUE_AGE_DAYS,
    MONITOR_CODE,
    MONITOR_NAME,
    other_currencies,
    value_code,
)
from common.market_climate_sql import DOMAIN

LENSES = [("us_dollar", "Against the US dollar", "USD"), ("australian_dollar", "Against the Australian dollar", "AUD")]
SHORT_BASE_NAMES = {"USD": "US dollar", "AUD": "Australian dollar"}


def series_values_sql() -> str:
    """VALUES rows (lens_code, lens_name, signal_code, signal_name, rate_code, base_name) of the currency rows."""
    rows = []
    for lens_code, lens_name, base in LENSES:
        for currency in other_currencies(base):
            rows.append(
                f"('{lens_code}', '{lens_name}', '{currency.code.lower()}', '{currency.name}', "
                f"'{value_code(currency.code, base)}', '{SHORT_BASE_NAMES[base]}')"
            )
    return ", ".join(rows)


BAND = "CASE WHEN {value} <= {average} THEN 'red' WHEN {change} > 0 THEN 'green' ELSE 'yellow' END"


def currency_signal_query(domain: str = DOMAIN, indicator_source: str | None = None) -> str:
    """Currency rows. A currency or index counts on a day when its value is at most MAX_VALUE_AGE_DAYS old."""
    indicator_source = indicator_source or f"{domain}.market_rate_indicator_daily"
    band = BAND.format(value="v.rate_value", average="v.average_value", change="v.average_change")
    index_band = BAND.format(value="x.value", average="x.average_value", change="x.average_change")
    return f"""
    WITH series AS (
      SELECT * FROM VALUES {series_values_sql()} AS series(lens_code, lens_name, signal_code, signal_name, rate_code, base_name)
    ), recent AS (
      SELECT * FROM {indicator_source}
      WHERE two_hundred_day_average_value IS NOT NULL
        AND observation_date >= date_sub(indicator_date, {MAX_VALUE_AGE_DAYS})
    ), valued AS (
      SELECT s.lens_code, s.lens_name, s.signal_code, s.signal_name, s.base_name, i.indicator_date AS signal_date,
             i.rate_value, i.two_hundred_day_average_value AS average_value,
             i.two_hundred_day_average_change_value AS average_change, i.ingested_timestamp
      FROM series s JOIN recent i ON i.rate_code = s.rate_code
    ), days AS (
      SELECT DISTINCT signal_date FROM valued
    ), dollar_index AS (
      SELECT d.signal_date, p.price_close_adjusted AS value, p.close_adjusted_two_hundred_day_average_amount AS average_value,
             p.close_adjusted_two_hundred_day_average_slope_ratio AS average_change, p.ingested_timestamp
      FROM days d
      JOIN {domain}.price_indicator_daily p
        ON p.trading_symbol_code = '{DOLLAR_INDEX_SYMBOL}'
       AND p.price_date <= d.signal_date AND p.price_date >= date_sub(d.signal_date, {MAX_VALUE_AGE_DAYS})
      WHERE p.close_adjusted_two_hundred_day_average_amount IS NOT NULL
      QUALIFY row_number() OVER (PARTITION BY d.signal_date ORDER BY p.price_date DESC) = 1
    ), broad_index AS (
      SELECT indicator_date AS signal_date, rate_value AS value, two_hundred_day_average_value AS average_value,
             two_hundred_day_average_change_value AS average_change, ingested_timestamp
      FROM recent WHERE rate_code = '{BROAD_INDEX_RATE_CODE}'
    ), indexes AS (
      SELECT signal_date, 'dollar_index' AS signal_code, 'US Dollar Index (DXY)' AS signal_name, 'US Dollar Index' AS label,
             value, average_value, average_change, ingested_timestamp FROM dollar_index
      UNION ALL
      SELECT signal_date, 'dollar_broad_index', 'Broad dollar index (Federal Reserve)', 'Federal Reserve broad dollar index',
             value, average_value, average_change, ingested_timestamp FROM broad_index
    ), currency_rows AS (
      SELECT v.signal_date, v.lens_code, v.lens_name, v.signal_code, v.signal_name,
             v.rate_value > v.average_value AS is_yes, {band} AS band_code,
             CAST(v.rate_value AS DECIMAL(18, 6)) AS measured_value, CAST(v.average_value AS DECIMAL(18, 6)) AS threshold_value,
             concat(v.signal_name, ' is worth ', CAST(round(v.rate_value, 6) AS STRING), ' ',
                    v.base_name, 's; its 200-day average is ', CAST(round(v.average_value, 6) AS STRING),
                    CASE WHEN v.rate_value > v.average_value THEN ', so it is gaining against the '
                         ELSE ', so it is losing against the ' END, v.base_name, '.') AS reason_text,
             v.ingested_timestamp
      FROM valued v
    )
    SELECT signal_date, '{MONITOR_CODE}' AS monitor_code, '{MONITOR_NAME}' AS monitor_name, lens_code, lens_name,
           signal_code, signal_name, is_yes, band_code, measured_value, threshold_value, reason_text,
           CAST(NULL AS BIGINT) AS yes_count, CAST(NULL AS STRING) AS action_name, ingested_timestamp
    FROM currency_rows
    UNION ALL
    SELECT x.signal_date, '{MONITOR_CODE}', '{MONITOR_NAME}', 'us_dollar', 'Against the US dollar', x.signal_code, x.signal_name,
           x.value > x.average_value, {index_band},
           CAST(x.value AS DECIMAL(18, 6)), CAST(x.average_value AS DECIMAL(18, 6)),
           concat('The ', x.label, ' is ', CAST(round(x.value, 4) AS STRING), ', ',
                  CASE WHEN x.value > x.average_value THEN 'above' ELSE 'at or below' END, ' its 200-day average of ',
                  CAST(round(x.average_value, 4) AS STRING), ', so the dollar is ',
                  CASE WHEN x.value > x.average_value THEN 'strong' ELSE 'weak' END, ' on this measure.'),
           CAST(NULL AS BIGINT), CAST(NULL AS STRING), x.ingested_timestamp
    FROM indexes x
    UNION ALL
    SELECT c.signal_date, '{MONITOR_CODE}', '{MONITOR_NAME}', c.lens_code, c.lens_name, 'summary', 'Currencies gaining',
           CAST(NULL AS BOOLEAN), 'blue', CAST(NULL AS DECIMAL(18, 6)), CAST(NULL AS DECIMAL(18, 6)),
           concat(count_if(c.is_yes), ' of ', count(*), ' currencies are gaining ',
                  CASE c.lens_code WHEN 'us_dollar' THEN 'against the US dollar' ELSE 'against the Australian dollar' END, '.'),
           CAST(count_if(c.is_yes) AS BIGINT), concat(count_if(c.is_yes), ' of ', count(*), ' gaining'), min(c.ingested_timestamp)
    FROM currency_rows c
    GROUP BY c.signal_date, c.lens_code, c.lens_name
    """
