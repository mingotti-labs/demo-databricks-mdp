# Silver Domain investments: listing (openspec silver-domain-investments). One trading
# symbol on one market; the market comes from Yahoo's exchange code. The latest Yahoo
# options row of the symbol is joined on as the option_* columns (one row per symbol).
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.investments import IDENTIFIER_SOURCE, entity_id_sql, market_code_sql  # noqa: E402

LANDING = "silver_landing"
OPEN_ENDED = "TIMESTAMP '9999-12-31'"


@dp.materialized_view(
    comment="One row per trading symbol on one market. listing_id is the SHA-256 hash of "
    "market_code and trading_symbol_code. company_id is empty for a benchmark. The option_* "
    "columns are the latest Yahoo options activity."
)
def listing():
    return spark.sql(
        f"""
        WITH members AS (
          SELECT symbol, cik,
                 min(ingested_timestamp) OVER (PARTITION BY symbol) AS first_ingested,
                 row_number() OVER (
                   PARTITION BY symbol
                   ORDER BY coalesce(scd_valid_to_timestamp, {OPEN_ENDED}) DESC,
                            scd_valid_from_timestamp DESC
                 ) AS version_rank
          FROM {LANDING}.wikipedia__sp500_constituents
        ), symbols AS (
          SELECT symbol, cik, first_ingested AS ingested_timestamp FROM members WHERE version_rank = 1
          UNION ALL
          SELECT symbol, CAST(NULL AS STRING), ingested_timestamp
          FROM {LANDING}.portfolio__benchmarks
          WHERE is_current AND symbol NOT IN (SELECT symbol FROM members)
        ), located AS (
          SELECT s.symbol AS trading_symbol_code,
                 s.cik,
                 {market_code_sql("c.exchange_code")} AS market_code,
                 lower(o.has_options) = 'true' AS has_options,
                 CAST(o.expiry_count AS BIGINT) AS option_expiry_count,
                 try_to_date(o.nearest_monthly_expiry) AS option_nearest_monthly_expiry_date,
                 CAST(CAST(o.open_interest AS DECIMAL(20, 0)) AS BIGINT) AS option_open_interest,
                 CAST(CAST(o.volume AS DECIMAL(20, 0)) AS BIGINT) AS option_volume,
                 least(s.ingested_timestamp, coalesce(c.ingested_timestamp, s.ingested_timestamp),
                       coalesce(o.ingested_timestamp, s.ingested_timestamp)) AS ingested_timestamp
          FROM symbols s
          LEFT JOIN {LANDING}.yahoo__calendar c ON c.symbol = s.symbol AND c.is_current
          LEFT JOIN {LANDING}.yahoo__options o ON o.symbol = s.symbol
        )
        SELECT {entity_id_sql("market_code", "trading_symbol_code")} AS listing_id,
               market_code,
               trading_symbol_code,
               'USD' AS currency_code,
               CASE WHEN cik IS NOT NULL
                    THEN {entity_id_sql(f"'{IDENTIFIER_SOURCE}'", "cik")} END AS company_id,
               has_options,
               option_expiry_count,
               option_nearest_monthly_expiry_date,
               option_open_interest,
               option_volume,
               ingested_timestamp
        FROM located
        """
    )
