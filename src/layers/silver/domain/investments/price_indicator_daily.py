# Silver Domain investments: price_indicator_daily (openspec market-climate-silver). A
# 200-day simple moving average of each listing's adjusted close, and its 20-day slope, and
# the 52-week high and low (openspec inflation-deflation-monitor), and the 60-day change, ranges
# and efficiency ratios of strategy 004 (openspec us-yields-and-efficiency-indicators).
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
  `close_sixty_day_change_amount` DECIMAL(18, 6) COMMENT 'Rate of change over 60 price rows in amount: price_close minus the price_close 60 rows earlier (reported close, split-corrected by Yahoo), in the listing currency. A rolling window that moves one day per row. Empty until 61 rows exist.',
  `close_sixty_day_change_ratio` DECIMAL(18, 8) COMMENT 'Rate of change over 60 price rows as a fraction: price_close divided by the price_close 60 rows earlier, minus 1 (0.30 means up 30%, negative means down). Empty until 61 rows exist.',
  `price_range_amount` DECIMAL(18, 6) COMMENT 'Daily range in amount: price_high minus price_low of the price date, in the listing currency.',
  `price_range_ratio` DECIMAL(18, 8) COMMENT 'Daily range as a fraction of the close: (price_high minus price_low) divided by price_close.',
  `true_range_amount` DECIMAL(18, 6) COMMENT 'True range in amount: the largest of price_high minus price_low, the absolute value of price_high minus the previous close and the absolute value of price_low minus the previous close (a gap from the previous close counts). Equals the daily range on the first row of a listing, which has no previous close.',
  `true_range_ratio` DECIMAL(18, 8) COMMENT 'True range as a fraction of the close: true_range_amount divided by price_close.',
  `price_range_sixty_day_average_amount` DECIMAL(18, 6) COMMENT 'ar amount SMA60: simple average of price_range_amount over the last 60 price rows up to and including price_date (trading days). A rolling window that moves one day per row. Empty until 60 rows exist.',
  `price_range_sixty_day_average_ratio` DECIMAL(18, 8) COMMENT 'Simple average of price_range_ratio over the last 60 price rows; the average daily range as a fraction of the close. Empty until 60 rows exist.',
  `true_range_sixty_day_average_amount` DECIMAL(18, 6) COMMENT 'atr amount SMA60 (average true range): simple average of true_range_amount over the last 60 price rows up to and including price_date. A rolling window that moves one day per row. Empty until 60 rows exist.',
  `true_range_sixty_day_average_ratio` DECIMAL(18, 8) COMMENT 'Simple average of true_range_ratio over the last 60 price rows; the average true range as a fraction of the close. Empty until 60 rows exist.',
  `efficiency_r60_ratio` DECIMAL(18, 6) COMMENT 'Efficiency ratio r60 of strategy 004: close_sixty_day_change_amount divided by price_range_sixty_day_average_amount (rate of change over 60 days in amount over ar amount SMA60; amount over amount, so it does not depend on the share price). 15 or more is the screening threshold; negative for a falling price. Empty when either is empty or the average is zero.',
  `efficiency_tr60_ratio` DECIMAL(18, 6) COMMENT 'Efficiency ratio tr60 of strategy 004: close_sixty_day_change_amount divided by true_range_sixty_day_average_amount (rate of change over 60 days in amount over atr amount SMA60). Empty when either is empty or the average is zero.',
  `volume_sixty_day_average_count` BIGINT COMMENT 'Average daily volume in shares: simple average of price_volume_count over the last 60 price rows up to and including price_date, rounded to a whole number. Empty until 60 rows exist.',
  `currency_code` STRING COMMENT 'Currency of the price (USD for the S&P 500 index level and US listings).',
  `ingested_timestamp` TIMESTAMP COMMENT 'When the price row was fetched.'
"""


@dp.materialized_view(
    comment="Per listing and price date: the 200-day simple moving average of the adjusted close and "
    "its 20-day slope (input to the market climate trend answer), the 52-week high and low, and the "
    "strategy 004 indicators: 60-day rate of change, daily range and true range with their 60-day "
    "averages, the efficiency ratios r60 and tr60 and the 60-day average volume.",
    schema=COLUMNS,
)
def price_indicator_daily():
    return spark.sql(
        """
        WITH ranges AS (
          SELECT *,
                 price_high - price_low AS price_range_amount,
                 greatest(
                   price_high - price_low,
                   abs(price_high - lag(price_close) OVER by_listing),
                   abs(price_low - lag(price_close) OVER by_listing)
                 ) AS true_range_amount
          FROM price_daily
          WINDOW by_listing AS (PARTITION BY listing_id ORDER BY price_date)
        ), windowed AS (
          SELECT listing_id,
                 trading_symbol_code,
                 price_date,
                 price_close_adjusted,
                 count(price_close_adjusted) OVER w AS close_adjusted_day_count,
                 avg(price_close_adjusted) OVER w AS window_average,
                 max(price_high) OVER year_range AS price_high_fifty_two_week_amount,
                 min(price_low) OVER year_range AS price_low_fifty_two_week_amount,
                 price_close - lag(price_close, 60) OVER by_listing AS close_sixty_day_change_amount,
                 price_close / lag(price_close, 60) OVER by_listing - 1 AS close_sixty_day_change_ratio,
                 price_range_amount,
                 price_range_amount / price_close AS price_range_ratio,
                 true_range_amount,
                 true_range_amount / price_close AS true_range_ratio,
                 count(price_range_amount) OVER w60 AS range_day_count,
                 avg(price_range_amount) OVER w60 AS range_average_amount,
                 avg(price_range_amount / price_close) OVER w60 AS range_average_ratio,
                 avg(true_range_amount) OVER w60 AS true_range_average_amount,
                 avg(true_range_amount / price_close) OVER w60 AS true_range_average_ratio,
                 avg(price_volume_count) OVER w60 AS volume_average_count,
                 currency_code,
                 ingested_timestamp
          FROM ranges
          WINDOW w AS (PARTITION BY listing_id ORDER BY price_date ROWS BETWEEN 199 PRECEDING AND CURRENT ROW),
                 w60 AS (PARTITION BY listing_id ORDER BY price_date ROWS BETWEEN 59 PRECEDING AND CURRENT ROW),
                 by_listing AS (PARTITION BY listing_id ORDER BY price_date),
                 year_range AS (PARTITION BY listing_id ORDER BY CAST(price_date AS TIMESTAMP)
                                RANGE BETWEEN INTERVAL 363 DAYS PRECEDING AND CURRENT ROW)
        ), averaged AS (
          SELECT *,
                 CASE WHEN close_adjusted_day_count = 200 THEN CAST(window_average AS DECIMAL(18, 6)) END
                   AS close_adjusted_two_hundred_day_average_amount,
                 CASE WHEN range_day_count = 60 THEN CAST(range_average_amount AS DECIMAL(18, 6)) END
                   AS price_range_sixty_day_average_amount,
                 CASE WHEN range_day_count = 60 THEN CAST(true_range_average_amount AS DECIMAL(18, 6)) END
                   AS true_range_sixty_day_average_amount
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
               CAST(close_sixty_day_change_amount AS DECIMAL(18, 6)) AS close_sixty_day_change_amount,
               CAST(close_sixty_day_change_ratio AS DECIMAL(18, 8)) AS close_sixty_day_change_ratio,
               CAST(price_range_amount AS DECIMAL(18, 6)) AS price_range_amount,
               CAST(price_range_ratio AS DECIMAL(18, 8)) AS price_range_ratio,
               CAST(true_range_amount AS DECIMAL(18, 6)) AS true_range_amount,
               CAST(true_range_ratio AS DECIMAL(18, 8)) AS true_range_ratio,
               price_range_sixty_day_average_amount,
               CAST(CASE WHEN range_day_count = 60 THEN range_average_ratio END AS DECIMAL(18, 8))
                 AS price_range_sixty_day_average_ratio,
               true_range_sixty_day_average_amount,
               CAST(CASE WHEN range_day_count = 60 THEN true_range_average_ratio END AS DECIMAL(18, 8))
                 AS true_range_sixty_day_average_ratio,
               CAST(close_sixty_day_change_amount / nullif(price_range_sixty_day_average_amount, 0)
                    AS DECIMAL(18, 6)) AS efficiency_r60_ratio,
               CAST(close_sixty_day_change_amount / nullif(true_range_sixty_day_average_amount, 0)
                    AS DECIMAL(18, 6)) AS efficiency_tr60_ratio,
               CAST(CASE WHEN range_day_count = 60 THEN round(volume_average_count) END AS BIGINT)
                 AS volume_sixty_day_average_count,
               currency_code,
               ingested_timestamp
        FROM averaged
        """
    )
