# Silver Domain investments: price_daily (openspec silver-domain-investments). Yahoo's
# daily prices typed and joined to listing.
from pyspark import pipelines as dp

LANDING = "silver_landing"


@dp.materialized_view(
    comment="Yahoo's daily open, high, low, close (as reported), adjusted close and volume per "
    "listing and price date."
)
def price_daily():
    return spark.sql(
        f"""
        SELECT l.listing_id,
               p.symbol AS trading_symbol_code,
               to_date(p.date) AS price_date,
               CAST(p.open AS DECIMAL(18, 6)) AS price_open,
               CAST(p.high AS DECIMAL(18, 6)) AS price_high,
               CAST(p.low AS DECIMAL(18, 6)) AS price_low,
               CAST(p.close AS DECIMAL(18, 6)) AS price_close,
               CAST(p.adj_close AS DECIMAL(18, 6)) AS price_close_adjusted,
               CAST(CAST(p.volume AS DECIMAL(20, 0)) AS BIGINT) AS price_volume_count,
               l.currency_code,
               p.ingested_timestamp
        FROM {LANDING}.yahoo__prices p
        JOIN listing l ON l.trading_symbol_code = p.symbol
        """
    )
