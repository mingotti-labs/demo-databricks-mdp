"""SQL of the market rate indicators (openspec inflation-deflation-monitor, currency-monitor).

Plain strings so a probe can run the exact query against dev before it goes into a pipeline. `prefix` is
empty inside the silver pipeline (bare dataset names) and `<catalog>.silver_domain_investments.` in a probe.
"""

from common.currency import (
    CURRENCIES,
    BASE_NAMES,
    carried_rate_codes,
    exchange_rate_codes,
    value_code,
    value_series,
    value_unit,
    value_in_us_dollars_sql,
)

CPI_RATE_CODE = "us_cpi_all_items_not_seasonally_adjusted"
FED_RATE_CODE = "us_federal_funds_effective_rate"
CPI_PREVIOUS_CODE = "us_cpi_change_previous_reading_percent"
CPI_TWELVE_CODE = "us_cpi_change_twelve_months_percent"
REAL_RATE_CODE = "us_real_federal_funds_rate"
AVERAGE_ROWS = 200
CHANGE_ROWS = 20


def codes_sql(codes: list[str]) -> str:
    return ", ".join(f"'{c}'" for c in codes)


def cross_rate_sql() -> str:
    """UNION ALL rows (rate_code, name, date, value, source date, unit, timestamp) of every currency's value in each base."""
    by_code = {c.code: c for c in CURRENCIES}
    usd_value = {c.code: value_in_us_dollars_sql(c, "{alias}.rate_value") for c in CURRENCIES if c.exchange_rate_code}
    blocks = []
    for currency, base in value_series():
        name = f"{currency.name} in {BASE_NAMES[base]} (value of one unit)"
        code = value_code(currency.code, base)
        if currency.code == "USD":
            numerator, source_a = "1", None
        else:
            numerator, source_a = usd_value[currency.code].format(alias="a"), currency.exchange_rate_code
        if base == "USD":
            value, join, dates, stamps = numerator, "", "a.observation_date", "a.ingested_timestamp"
            where = f"a.rate_code = '{source_a}'"
            frm = "fx a"
        else:
            base_rate = by_code[base].exchange_rate_code
            denominator = usd_value[base].format(alias="b")
            if source_a is None:
                value, frm = f"1 / ({denominator})", "fx b"
                where = f"b.rate_code = '{base_rate}'"
                dates, stamps = "b.observation_date", "b.ingested_timestamp"
            else:
                value = f"({numerator}) / ({denominator})"
                frm = "fx a JOIN fx b ON a.indicator_date = b.indicator_date"
                where = f"a.rate_code = '{source_a}' AND b.rate_code = '{base_rate}'"
                dates, stamps = "least(a.observation_date, b.observation_date)", "least(a.ingested_timestamp, b.ingested_timestamp)"
        indicator_date = "b.indicator_date" if (base != "USD" and source_a is None) else "a.indicator_date"
        blocks.append(
            f"SELECT '{code}', '{name}', {indicator_date}, {value}, {dates}, '{value_unit(base)}', true, {stamps} FROM {frm} WHERE {where}"
        )
    return "\n      UNION ALL\n      ".join(blocks)


def market_rate_indicator_query(prefix: str = "") -> str:
    """Per series and `^GSPC` trading day: the value known that day, its 200-row average and the average's change."""
    return f"""
    WITH days AS (
      SELECT DISTINCT price_date AS indicator_date FROM {prefix}price_daily WHERE trading_symbol_code = '^GSPC'
    ), readings AS (
      SELECT observation_date, rate_value, ingested_timestamp FROM {prefix}market_rate_daily
      WHERE rate_code = '{CPI_RATE_CODE}' AND NOT is_carried_forward
    ), changes AS (
      SELECT r.observation_date, r.ingested_timestamp,
             (r.rate_value / lag(r.rate_value) OVER (ORDER BY r.observation_date) - 1) * 100 AS previous_change,
             (r.rate_value / y.rate_value - 1) * 100 AS twelve_change
      FROM readings r LEFT JOIN readings y ON y.observation_date = add_months(r.observation_date, -12)
    ), observed AS (
      SELECT rate_code, rate_name, observation_date, rate_value, unit_name, false AS is_calculated, ingested_timestamp
      FROM {prefix}market_rate_daily
      WHERE rate_code IN ('{CPI_RATE_CODE}', '{FED_RATE_CODE}', {codes_sql(carried_rate_codes() + exchange_rate_codes())})
      UNION ALL
      SELECT '{CPI_PREVIOUS_CODE}', 'US CPI change against the previous reading, percent', observation_date,
             previous_change, 'percent', true, ingested_timestamp FROM changes WHERE previous_change IS NOT NULL
      UNION ALL
      SELECT '{CPI_TWELVE_CODE}', 'US CPI change over 12 months, percent', observation_date,
             twelve_change, 'percent', true, ingested_timestamp FROM changes WHERE twelve_change IS NOT NULL
    ), series AS (
      SELECT DISTINCT rate_code, rate_name, unit_name, is_calculated FROM observed
    ), points AS (
      SELECT rate_code, observation_date AS point_date, rate_value, ingested_timestamp, false AS is_day FROM observed
      UNION ALL
      SELECT s.rate_code, d.indicator_date, CAST(NULL AS DECIMAL(18, 6)), CAST(NULL AS TIMESTAMP), true
      FROM series s CROSS JOIN days d
    ), filled AS (
      SELECT rate_code, point_date AS indicator_date, is_day,
             last(rate_value, true) OVER w AS rate_value,
             last(CASE WHEN rate_value IS NOT NULL THEN point_date END, true) OVER w AS observation_date,
             last(ingested_timestamp, true) OVER w AS ingested_timestamp
      FROM points
      WINDOW w AS (PARTITION BY rate_code ORDER BY point_date, is_day ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
    ), known AS (
      SELECT f.rate_code, s.rate_name, f.indicator_date, f.rate_value, f.observation_date, s.unit_name,
             s.is_calculated, f.ingested_timestamp
      FROM filled f JOIN series s ON s.rate_code = f.rate_code WHERE f.is_day AND f.rate_value IS NOT NULL
    ), fx AS (
      SELECT rate_code, indicator_date, rate_value, observation_date, ingested_timestamp
      FROM known WHERE rate_code IN ({codes_sql(exchange_rate_codes())})
    ), combined AS (
      SELECT * FROM known WHERE rate_code NOT IN ({codes_sql(exchange_rate_codes())})
      UNION ALL
      SELECT '{REAL_RATE_CODE}', 'US real federal funds rate (effective rate minus CPI change over 12 months), percent',
             a.indicator_date, a.rate_value - b.rate_value, least(a.observation_date, b.observation_date),
             'percent', true, least(a.ingested_timestamp, b.ingested_timestamp)
      FROM known a JOIN known b ON a.indicator_date = b.indicator_date
      WHERE a.rate_code = '{FED_RATE_CODE}' AND b.rate_code = '{CPI_TWELVE_CODE}'
      UNION ALL
      {cross_rate_sql()}
    ), averaged AS (
      SELECT *,
             count(rate_value) OVER w AS day_count,
             avg(rate_value) OVER w AS window_average
      FROM combined
      WINDOW w AS (PARTITION BY rate_code ORDER BY indicator_date ROWS BETWEEN {AVERAGE_ROWS - 1} PRECEDING AND CURRENT ROW)
    ), measured AS (
      SELECT *, CASE WHEN day_count = {AVERAGE_ROWS} THEN window_average END AS average_value FROM averaged
    )
    SELECT rate_code, rate_name, indicator_date,
           CAST(rate_value AS DECIMAL(28, 12)) AS rate_value,
           observation_date,
           CAST(average_value AS DECIMAL(28, 12)) AS two_hundred_day_average_value,
           CAST(average_value - lag(average_value, {CHANGE_ROWS}) OVER (PARTITION BY rate_code ORDER BY indicator_date)
                AS DECIMAL(28, 12)) AS two_hundred_day_average_change_value,
           CAST(day_count AS BIGINT) AS day_count,
           is_calculated, unit_name, ingested_timestamp
    FROM measured
    """
