# Gold analytics gateway: index_valuation_daily (openspec market-climate-gold). The S&P 500's market
# value, earnings totals and price/earnings ratios per day, from silver_domain_investments. The query
# is in common/market_climate_sql.py so a probe can run the same text.
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.investments import schema_with_comments  # noqa: E402
from common.market_climate_sql import index_valuation_query  # noqa: E402

COMMENTS = {
    "index_code": "Index the row describes. SP500 is the S&P 500: its current members, one listing per company.",
    "valuation_date": (
        "Trading day (an S&P 500 index price date) the figures are as of. Point in time: each member's price, "
        "share count and earnings are those known on this day. The index members are today's members for every "
        "day, so older days are approximate."
    ),
    "market_value_amount": (
        "Total market value in US dollars of the members used that day: closing price times shares "
        "(the cover-page share count, else the weighted average basic shares)."
    ),
    "earnings_trailing_twelve_months_amount": (
        "Sum over the members used of net income over the last twelve months, in US dollars, not adjusted for "
        "inflation. A rolling window that moves one quarter per filing."
    ),
    "earnings_ten_year_average_amount": (
        "Sum over the members used of each member's average annual net income over its last up to 10 fiscal "
        "years, in US dollars, NOT adjusted for inflation. A rolling window that moves one year per 10-K."
    ),
    "earnings_ten_year_average_inflation_adjusted_amount": (
        "The same 10-year average with every year first converted into today's money (US consumer prices on "
        "this valuation_date). A rolling window. This is the earnings figure behind the 10-year "
        "inflation-adjusted price/earnings ratio that the market climate valuation vote uses."
    ),
    "price_earnings_trailing_twelve_months_ratio": (
        "market_value_amount divided by earnings_trailing_twelve_months_amount. Simple, but it swings with the "
        "business cycle: earnings fall faster than prices in a recession, so the ratio jumps. Empty when "
        "earnings are not positive."
    ),
    "price_earnings_ten_year_average_ratio": (
        "market_value_amount divided by earnings_ten_year_average_amount. Smooths the cycle but ignores "
        "inflation, so it is overstated: old dollars bought more. Shown for comparison; it does not vote."
    ),
    "price_earnings_ten_year_average_inflation_adjusted_ratio": (
        "market_value_amount divided by earnings_ten_year_average_inflation_adjusted_amount: price over the "
        "10-year average of earnings in today's money (a CAPE-like ratio). This is the ratio the market climate "
        "valuation answer uses: too expensive when above 22 (long run lens) or 30 (modern lens)."
    ),
    "consumer_price_index_value": (
        "US consumer price index (all items, not seasonally adjusted) in index points, of the latest month "
        "with a value on or before valuation_date. Used as today's money for the inflation adjustment."
    ),
    "member_count": "Number of current S&P 500 members counted, one listing per company (a company with two share classes counts once).",
    "members_used_count": (
        "Members that have, on valuation_date, a price (at most 5 days old), a share count, net income and both "
        "10-year averages. Only these are in the totals above."
    ),
    "members_without_shares_count": (
        "Members with a price but no share count (neither cover-page nor weighted average) on their latest "
        "filing. They are left out of the totals, so a high count weakens the ratios."
    ),
    "members_under_ten_years_count": (
        "Used members with fewer than 10 fiscal years of annual earnings on file; their 10-year averages "
        "cover fewer years."
    ),
    "currency_code": "Currency of the amounts: USD.",
    "ingested_timestamp": "Earliest fetch time of the price and filing rows behind this day's totals.",
}

COLUMNS = [(f.name, f.dataType.simpleString()) for f in spark.sql(index_valuation_query()).schema.fields]


@dp.materialized_view(
    comment="S&P 500 valuation per day: market value, trailing 12-month and 10-year (plain and inflation-adjusted) "
    "earnings, and the three price/earnings ratios with the member counts behind them. One row per index and day.",
    schema=schema_with_comments(COLUMNS, COMMENTS),
)
def index_valuation_daily():
    return spark.sql(index_valuation_query())
