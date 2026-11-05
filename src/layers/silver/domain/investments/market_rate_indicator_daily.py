# Silver Domain investments: market_rate_indicator_daily (openspec inflation-deflation-monitor, currency-monitor). The US CPI
# index, its changes, the federal funds effective rate and the real rate, the value of each main currency in US and
# Australian dollars, the broad dollar index and the interest rates of the main countries on every S&P 500 trading day,
# each with its 200-day average and how that average moved. The query is in common/market_rate_indicator_sql.py.
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.market_rate_indicator_sql import market_rate_indicator_query  # noqa: E402

COLUMNS = """
  `rate_code` STRING COMMENT 'Series: us_cpi_all_items_not_seasonally_adjusted (the CPI index, index points), us_federal_funds_effective_rate (the short-term rate, percent), us_cpi_change_previous_reading_percent (CPI against the previous monthly reading, percent), us_cpi_change_twelve_months_percent (CPI against the reading 12 months earlier, percent) and us_real_federal_funds_rate (effective rate minus the 12-month CPI change, percent); currency_value_<code>_in_usd and currency_value_<code>_in_aud (the value of one unit of a main currency in US or Australian dollars, for example currency_value_chf_in_aud, worked out from the FRED exchange rates: a rate quoted as units per US dollar is inverted, and the value in Australian dollars is the value in US dollars divided by the value of one Australian dollar in US dollars on the same day); us_dollar_broad_index (Federal Reserve broad dollar index); and the short-term and 10-year interest rates of the main countries as in market_rate_daily (for example japan_3_month_interbank_rate, uk_10_year_government_bond_yield). Joins to market_rate_daily.rate_code for the series that are reported.',
  `rate_name` STRING COMMENT 'Display name of the series.',
  `indicator_date` DATE COMMENT 'Trading day of the S&P 500 (a ^GSPC price date). One row per series and trading day, from 1970-01-02.',
  `rate_value` DECIMAL(28, 12) COMMENT 'Value of the series known on indicator_date: the latest reading on or before that day, carried forward until the next one. Unit in unit_name. The CPI changes are worked out on the monthly CPI readings only (not on carried days) and then carried.',
  `observation_date` DATE COMMENT 'Date of the reading behind rate_value (for the real rate, the older of its two parts); a gap to indicator_date means the reading has not arrived yet (FRED lags a few days, its exchange rates up to about 10) or that the series is monthly (CPI, the OECD interest rates).',
  `two_hundred_day_average_value` DECIMAL(28, 12) COMMENT 'Simple moving average of rate_value over the last 200 rows of the series up to and including indicator_date (trading days, not calendar days). A rolling window that moves one day per row. Empty until 200 rows exist.',
  `two_hundred_day_average_change_value` DECIMAL(28, 12) COMMENT 'Direction of the 200-day average: the average minus the same average 20 rows earlier, in the unit of the series (positive is rising, negative falling). A difference, not a ratio, because the changes and the real rate can be zero or negative. Empty until the average has existed for 20 rows.',
  `day_count` BIGINT COMMENT 'Number of rows in the 200-row window (at most 200); under 200 means too little history for the average.',
  `is_calculated` BOOLEAN COMMENT 'True for the series worked out here (the two CPI changes, the real rate and the currency values); false for the reported series (CPI index, broad dollar index and the interest rates).',
  `unit_name` STRING COMMENT 'index_points for the CPI index and the broad dollar index, percent for the changes, the real rate and the interest rates, us_dollars_per_unit or australian_dollars_per_unit for a currency value.',
  `ingested_timestamp` TIMESTAMP COMMENT 'Earliest fetch time of the readings behind rate_value.'
"""


@dp.materialized_view(
    comment="US CPI index, its changes, the federal funds effective rate and the real rate per S&P 500 trading day, each "
    "with its 200-day average and the average's 20-row change. Input to the inflation/deflation stars.",
    schema=COLUMNS,
)
def market_rate_indicator_daily():
    return spark.sql(market_rate_indicator_query())
