# Silver Domain investments, part 1: the entities. Materialized views over
# silver_landing only (openspec silver-domain-investments). company groups the
# Wikipedia S&P 500 versions by SEC central index key; market keeps the ISO 10383
# operating markets; listing is one trading symbol on one market, its market taken
# from Yahoo's exchange code; index_membership types the Wikipedia SCD2 versions.
# Entity ids are hashes of the business key, identical on every rebuild.
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.investments import IDENTIFIER_SOURCE, entity_id_sql, market_code_sql  # noqa: E402

LANDING = "silver_landing"
OPEN_ENDED = "TIMESTAMP '9999-12-31'"


@dp.materialized_view(
    comment="One row per SEC central index key that is or was in the S&P 500 list. company_id is "
    "the SHA-256 hash of identifier_source and central_index_key, opaque."
)
def company():
    return spark.sql(
        f"""
        SELECT {entity_id_sql(f"'{IDENTIFIER_SOURCE}'", "cik")} AS company_id,
               '{IDENTIFIER_SOURCE}' AS identifier_source,
               cik AS central_index_key,
               security AS company_name,
               gics_sector AS sector,
               gics_sub_industry AS sub_industry,
               first_ingested AS ingested_timestamp
        FROM (
          SELECT cik, security, gics_sector, gics_sub_industry,
                 min(ingested_timestamp) OVER (PARTITION BY cik) AS first_ingested,
                 row_number() OVER (
                   PARTITION BY cik
                   ORDER BY coalesce(scd_valid_to_timestamp, {OPEN_ENDED}) DESC, symbol
                 ) AS version_rank
          FROM {LANDING}.wikipedia__sp500_constituents
        )
        WHERE version_rank = 1
        """
    )


@dp.materialized_view(comment="One row per ISO 10383 operating market (market segments are left out).")
def market():
    return spark.sql(
        f"""
        SELECT market_identifier_code,
               market_name,
               legal_entity_name,
               country_code_alpha2,
               city,
               website,
               status,
               ingested_timestamp
        FROM {LANDING}.iso__market_identifier_codes
        WHERE is_current AND operating_or_segment = 'OPRT'
        """
    )


@dp.materialized_view(
    comment="One row per trading symbol on one market. listing_id is the SHA-256 hash of "
    "market_identifier_code and trading_symbol_code. company_id is empty for a benchmark."
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
                 {market_code_sql("c.exchange_code")} AS market_identifier_code,
                 least(s.ingested_timestamp, coalesce(c.ingested_timestamp, s.ingested_timestamp))
                   AS ingested_timestamp
          FROM symbols s
          LEFT JOIN {LANDING}.yahoo__calendar c ON c.symbol = s.symbol AND c.is_current
        )
        SELECT {entity_id_sql("market_identifier_code", "trading_symbol_code")} AS listing_id,
               market_identifier_code,
               trading_symbol_code,
               'USD' AS currency_code,
               CASE WHEN cik IS NOT NULL
                    THEN {entity_id_sql(f"'{IDENTIFIER_SOURCE}'", "cik")} END AS company_id,
               ingested_timestamp
        FROM located
        """
    )


@dp.materialized_view(comment="One row per listing per S&P 500 membership version.")
def index_membership():
    return spark.sql(
        f"""
        SELECT 'SP500' AS index_code,
               l.listing_id,
               w.symbol AS trading_symbol_code,
               try_to_date(w.date_added) AS date_added,
               w.scd_valid_from_timestamp AS valid_from_timestamp,
               w.scd_valid_to_timestamp AS valid_to_timestamp,
               w.is_current,
               w.ingested_timestamp
        FROM {LANDING}.wikipedia__sp500_constituents w
        JOIN listing l ON l.trading_symbol_code = w.symbol
        """
    )
