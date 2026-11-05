# Silver Domain investments: market_rate_indicator_daily (openspec inflation-deflation-monitor). The US CPI index,
# its changes, the federal funds effective rate and the real rate on every S&P 500 trading day, each with its
# 200-day average and how that average moved. The query is in common/inflation_sql.py.
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.inflation_sql import market_rate_indicator_query  # noqa: E402

COLUMNS = """
  `rate_code` STRING COMMENT 'Series: us_cpi_all_items_not_seasonally_adjusted (the CPI index, index points), us_federal_funds_effective_rate (the short-term rate, percent), us_cpi_change_previous_reading_percent (CPI against the previous monthly reading, percent), us_cpi_change_twelve_months_percent (CPI against the reading 12 months earlier, percent) and us_real_federal_funds_rate (effective rate minus the 12-month CPI change, percent). Joins to market_rate_daily.rate_code for the two reported series.',
  `rate_name` STRING COMMENT 'Display name of the series.',
  `indicator_date` DATE COMMENT 'Trading day of the S&P 500 (a ^GSPC price date). One row per series and trading day, from 1970-01-02.',
  `rate_value` DECIMAL(18, 6) COMMENT 'Value of the series known on indicator_date: the latest reading on or before that day, carried forward until the next one. Unit in unit_name. The CPI changes are worked out on the monthly CPI readings only (not on carried days) and then carried.',
  `observation_date` DATE COMMENT 'Date of the reading behind rate_value (for the real rate, the older of its two parts); a gap to indicator_date means the reading has not arrived yet (FRED lags a few days) or, for CPI, that the month has one reading.',
  `two_hundred_day_average_value` DECIMAL(18, 6) COMMENT 'Simple moving average of rate_value over the last 200 rows of the series up to and including indicator_date (trading days, not calendar days). A rolling window that moves one day per row. Empty until 200 rows exist.',
  `two_hundred_day_average_change_value` DECIMAL(18, 6) COMMENT 'Direction of the 200-day average: the average minus the same average 20 rows earlier, in the unit of the series (positive is rising, negative falling). A difference, not a ratio, because the changes and the real rate can be zero or negative. Empty until the average has existed for 20 rows.',
  `day_count` BIGINT COMMENT 'Number of rows in the 200-row window (at most 200); under 200 means too little history for the average.',
  `is_calculated` BOOLEAN COMMENT 'True for the series worked out here (the two CPI changes and the real rate); false for the reported series (CPI index and effective rate).',
  `unit_name` STRING COMMENT 'index_points for the CPI index, percent for the others.',
  `ingested_timestamp` TIMESTAMP COMMENT 'Earliest fetch time of the readings behind rate_value.'
"""


@dp.materialized_view(
    comment="US CPI index, its changes, the federal funds effective rate and the real rate per S&P 500 trading day, each "
    "with its 200-day average and the average's 20-row change. Input to the inflation/deflation stars.",
    schema=COLUMNS,
)
def market_rate_indicator_daily():
    return spark.sql(market_rate_indicator_query())
