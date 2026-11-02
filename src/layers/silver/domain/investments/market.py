# Silver Domain investments: market (openspec silver-domain-investments). The ISO 10383
# operating markets; market segments are left out.
from pyspark import pipelines as dp

LANDING = "silver_landing"


@dp.materialized_view(
    comment="One row per ISO 10383 operating market (market segments are left out). market_code "
    "is the ISO 10383 market identifier code."
)
def market():
    return spark.sql(
        f"""
        SELECT market_identifier_code AS market_code,
               market_name,
               legal_entity_name,
               country_code_alpha2 AS country_code,
               city AS city_name,
               website AS website_url,
               status AS status_name,
               ingested_timestamp
        FROM {LANDING}.iso__market_identifier_codes
        WHERE is_current AND operating_or_segment = 'OPRT'
        """
    )
