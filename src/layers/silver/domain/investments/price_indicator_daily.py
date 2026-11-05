# Silver Domain investments: price_indicator_daily (openspec market-climate-silver). A
# 200-day simple moving average of each listing's adjusted close, and its 20-day slope, and
# the 52-week high and low (openspec inflation-deflation-monitor).
from pyspark import pipelines as dp

COLUMNS = """
  `listing_id` STRING COMMENT 'Hash of market code and trading symbol; joins to listing.listing_id and price_daily.listing_id.',
  `trading_symbol_code` STRING COMMENT 'Yahoo ticker symbol of the listing, for example ^GSPC for the S&P 500 index level.',
  `price_date` DATE COMMENT 'Trading date; one row per listing and date, like price_daily.',
  `price_close_adjusted` DECIMAL(18, 6) COMMENT 'Yahoo adjusted close (corrected for splits and dividends; for an index equal to the close).',
  `close_adjusted_two_hundred_day_average_amount` DECIMAL(18, 6) COMMENT 'Simple moving average of price_close_adjusted over the last 200 price rows of the listing up to and including price_date (trading days, not calendar days). A rolling window that moves one day per row. Empty until 200 rows exist.',
  `close_adjusted_two_hundred_day_average_slope_ratio` DECIMAL(18, 8) COMMENT 'Direction of the 200-day average: the average divided by the same average 20 price rows earlier, minus 1 (0.012 means up 1.2% over about a month, negative means falling). Empty until the average has existed for 20 rows.',
  `close_adjusted_day_count` BIGINT COMMENT 'Number of price rows in the 200-row window (at most 200); under 200 means too little history for the average.',
  `price_high_fifty_two_week_amount` DECIMAL(18, 6) COMMENT 'Highest price_high of the listing over the price dates in the 364 days up to and including price_date (a 52-week high; reported, not adjusted, prices, as finance sites show it). A rolling window that moves one day per row; shorter than 52 weeks for a listing with less history.',
  `price_low_fifty_two_week_amount` DECIMAL(18, 6) COMMENT 'Lowest price_low of the listing over the price dates in the 364 days up to and including price_date (a 52-week low; reported, not adjusted, prices). A rolling window that moves one day per row.',
  `currency_code` STRING COMMENT 'Currency of the price (USD for the S&P 500 index level and US listings).',
  `ingested_timestamp` TIMESTAMP COMMENT 'When the price row was fetched.'
"""


@dp.materialized_view(
    comment="Per listing and price date: the 200-day simple moving average of the adjusted close and "
    "its 20-day slope. Input to the market climate trend answer (S&P 500 above its 200-day average).",
    schema=COLUMNS,
)
def price_indicator_daily():
    return spark.sql(
        """
        WITH windowed AS (
          SELECT listing_id,
                 trading_symbol_code,
                 price_date,
                 price_close_adjusted,
                 count(price_close_adjusted) OVER w AS close_adjusted_day_count,
                 avg(price_close_adjusted) OVER w AS window_average,
                 max(price_high) OVER year_range AS price_high_fifty_two_week_amount,
                 min(price_low) OVER year_range AS price_low_fifty_two_week_amount,
                 currency_code,
                 ingested_timestamp
          FROM price_daily
          WINDOW w AS (PARTITION BY listing_id ORDER BY price_date ROWS BETWEEN 199 PRECEDING AND CURRENT ROW),
                 year_range AS (PARTITION BY listing_id ORDER BY CAST(price_date AS TIMESTAMP)
                                RANGE BETWEEN INTERVAL 363 DAYS PRECEDING AND CURRENT ROW)
        ), averaged AS (
          SELECT *,
                 CASE WHEN close_adjusted_day_count = 200 THEN CAST(window_average AS DECIMAL(18, 6)) END
                   AS close_adjusted_two_hundred_day_average_amount
          FROM windowed
        )
        SELECT listing_id,
               trading_symbol_code,
               price_date,
               price_close_adjusted,
               close_adjusted_two_hundred_day_average_amount,
               CAST(
                 close_adjusted_two_hundred_day_average_amount
                 / lag(close_adjusted_two_hundred_day_average_amount, 20)
                     OVER (PARTITION BY listing_id ORDER BY price_date) - 1
                 AS DECIMAL(18, 8)
               ) AS close_adjusted_two_hundred_day_average_slope_ratio,
               close_adjusted_day_count,
               CAST(price_high_fifty_two_week_amount AS DECIMAL(18, 6)) AS price_high_fifty_two_week_amount,
               CAST(price_low_fifty_two_week_amount AS DECIMAL(18, 6)) AS price_low_fifty_two_week_amount,
               currency_code,
               ingested_timestamp
        FROM averaged
        """
    )
