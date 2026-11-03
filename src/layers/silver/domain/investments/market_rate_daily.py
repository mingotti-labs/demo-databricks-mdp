# Silver Domain investments: market_rate_daily (openspec silver-domain-investments,
# cpi-daily-carry-forward). Exchange and interest rates from RBA and FRED, plus CPI from
# FRED and the ABS carried onto business days.
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.investments import cpi_values_sql, rate_values_sql  # noqa: E402

LANDING = "silver_landing"


@dp.materialized_view(
    comment="Exchange and interest rates, one row per rate and date, and CPI carried forward "
    "onto business days (is_carried_forward marks the repeated rows)."
)
def market_rate_daily():
    return spark.sql(
        f"""
        WITH observations AS (
          SELECT 'rba' AS source, series_id, observation_date, value, ingested_timestamp
          FROM {LANDING}.rba__observations
          UNION ALL
          SELECT 'fred', series_id, observation_date, value, ingested_timestamp
          FROM {LANDING}.fred__observations
        ), rates AS (
          SELECT * FROM VALUES {rate_values_sql()} AS rates(rate_code, rate_name, source, series_id, unit)
        ), daily AS (
          SELECT r.rate_code,
                 r.rate_name,
                 o.observation_date,
                 CAST(o.value AS DECIMAL(18, 6)) AS rate_value,
                 r.unit AS unit_name,
                 r.source AS source_system_code,
                 r.series_id AS source_series_id,
                 o.ingested_timestamp,
                 false AS is_carried_forward
          FROM observations o
          JOIN rates r ON r.source = o.source AND r.series_id = o.series_id
          WHERE try_cast(o.value AS DECIMAL(18, 6)) IS NOT NULL
        ), cpi_series AS (
          SELECT * FROM VALUES {cpi_values_sql()} AS cpi(rate_code, rate_name, source, series_id, unit)
        ), cpi_periods AS (
          SELECT 'fred' AS source, series_id, observation_date AS period_start, value, ingested_timestamp
          FROM {LANDING}.fred__observations
          UNION ALL
          SELECT 'abs',
                 series_key,
                 CASE WHEN time_period LIKE '%-Q%'
                      THEN make_date(CAST(substr(time_period, 1, 4) AS INT),
                                     CAST(substr(time_period, 7, 1) AS INT) * 3 - 2, 1)
                      ELSE to_date(concat(time_period, '-01')) END,
                 value,
                 ingested_timestamp
          FROM {LANDING}.abs__observations
          WHERE is_current
        ), cpi_ranges AS (
          SELECT s.*, p.period_start, p.value, p.ingested_timestamp,
                 lead(p.period_start) OVER (PARTITION BY s.rate_code ORDER BY p.period_start) AS next_start
          FROM cpi_periods p
          JOIN cpi_series s ON s.source = p.source AND s.series_id = p.series_id
          WHERE try_cast(p.value AS DECIMAL(18, 6)) IS NOT NULL
        ), cpi_days AS (
          SELECT c.*, explode(sequence(c.period_start,
                                       coalesce(date_sub(c.next_start, 1), (SELECT max(observation_date) FROM daily)))) AS day
          FROM cpi_ranges c
          WHERE c.period_start <= (SELECT max(observation_date) FROM daily)
        ), cpi_weekdays AS (
          SELECT *, row_number() OVER (PARTITION BY rate_code, period_start ORDER BY day) AS day_in_period
          FROM cpi_days
          WHERE dayofweek(day) BETWEEN 2 AND 6
        )
        SELECT rate_code, rate_name, observation_date, rate_value, unit_name, source_system_code,
               source_series_id, ingested_timestamp, is_carried_forward
        FROM daily
        UNION ALL
        SELECT rate_code,
               rate_name,
               day,
               CAST(value AS DECIMAL(18, 6)),
               unit,
               source,
               series_id,
               ingested_timestamp,
               day_in_period > 1
        FROM cpi_weekdays
        """
    )
