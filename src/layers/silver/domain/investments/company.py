# Silver Domain investments: company (openspec silver-domain-investments). Groups the
# Wikipedia S&P 500 versions by SEC central index key. The id is a hash of the business
# key, identical on every rebuild.
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.investments import IDENTIFIER_SOURCE, entity_id_sql  # noqa: E402

LANDING = "silver_landing"
OPEN_ENDED = "TIMESTAMP '9999-12-31'"


@dp.materialized_view(
    comment="One row per SEC central index key that is or was in the S&P 500 list. company_id is "
    "the SHA-256 hash of identifier_source_system_code and central_index_key, opaque."
)
def company():
    return spark.sql(
        f"""
        SELECT {entity_id_sql(f"'{IDENTIFIER_SOURCE}'", "cik")} AS company_id,
               '{IDENTIFIER_SOURCE}' AS identifier_source_system_code,
               cik AS central_index_key,
               security AS company_name,
               gics_sector AS gics_sector_name,
               gics_sub_industry AS gics_sub_industry_name,
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
