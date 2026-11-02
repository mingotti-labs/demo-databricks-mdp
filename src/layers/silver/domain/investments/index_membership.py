# Silver Domain investments: index_membership (openspec silver-domain-investments).
# Types the Wikipedia SCD2 versions; a current version ends 9999-12-31, not NULL, so
# consumers can use plain BETWEEN joins.
from pyspark import pipelines as dp

LANDING = "silver_landing"
OPEN_ENDED = "TIMESTAMP '9999-12-31'"


@dp.materialized_view(comment="One row per listing per S&P 500 membership version.")
def index_membership():
    return spark.sql(
        f"""
        SELECT 'SP500' AS index_code,
               l.listing_id,
               w.symbol AS trading_symbol_code,
               try_to_date(w.date_added) AS date_added,
               w.scd_valid_from_timestamp AS valid_from_timestamp,
               coalesce(w.scd_valid_to_timestamp, {OPEN_ENDED}) AS valid_to_timestamp,
               w.is_current,
               w.ingested_timestamp
        FROM {LANDING}.wikipedia__sp500_constituents w
        JOIN listing l ON l.trading_symbol_code = w.symbol
        """
    )
