# Silver Domain investments: market_rate_daily (openspec silver-domain-investments).
# Exchange and interest rates from RBA and FRED in one table, picked by the RATES list.
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.investments import rate_values_sql  # noqa: E402

LANDING = "silver_landing"


@dp.materialized_view(comment="Exchange and interest rates in one table, one row per rate and date.")
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
        )
        SELECT r.rate_code,
               r.rate_name,
               o.observation_date,
               CAST(o.value AS DECIMAL(18, 6)) AS rate_value,
               r.unit AS unit_name,
               r.source AS source_system_code,
               r.series_id AS source_series_id,
               o.ingested_timestamp
        FROM observations o
        JOIN rates r ON r.source = o.source AND r.series_id = o.series_id
        WHERE try_cast(o.value AS DECIMAL(18, 6)) IS NOT NULL
        """
    )
