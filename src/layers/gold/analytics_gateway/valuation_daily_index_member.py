# Gold analytics gateway: valuation_daily_index_member (openspec market-climate-dashboard). One row per
# current S&P 500 member and day with everything behind the index valuation: the inputs, whether the member
# counts that day, and how much it moves the index price/earnings ratio. valuation_daily_index is the sum of
# its used rows. The query is in common/market_climate_sql.py so a probe can run the same text.
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.investments import schema_with_comments  # noqa: E402
from common.market_climate_sql import index_member_valuation_query  # noqa: E402

COMMENTS = {
    "index_code": "Index the row belongs to. SP500 is the S&P 500.",
    "valuation_date": (
        "Trading day (an S&P 500 index price date) the figures are as of. Point in time: the price, share "
        "count and earnings are those known on this day. The members are today's members for every day, so "
        "older days are approximate. Join to valuation_daily_index on index_code and valuation_date."
    ),
    "company_id": (
        "The member company (one row per company: a company with two share classes appears once, with its "
        "most traded listing). Join to silver_domain_investments.company on company_id for the name and "
        "gics_sector_name (today's sector)."
    ),
    "listing_id": "The listing (trading symbol on a market) whose price is used: the company's most traded one over its last 60 price rows.",
    "price_date": "Date of the closing price used: the latest price on or before valuation_date, at most 5 days earlier. Empty when there is none.",
    "filing_valid_from_date": (
        "Filing date of the 10-K or 10-Q in force on valuation_date (the company_fundamentals row valid that "
        "day). Empty when the company has no filing yet."
    ),
    "price_close": "Closing price of the listing on price_date, in US dollars per share.",
    "share_count": "Shares used: the cover-page share count of the filing, else the weighted average basic shares.",
    "share_count_source_code": "Where share_count came from: cover_page or weighted_average. Empty when there is no share count.",
    "earnings_trailing_twelve_months_amount": (
        "Net income over the last twelve months of the filing in force, in US dollars, not adjusted for "
        "inflation. A rolling window that moves one quarter per filing."
    ),
    "revenue_trailing_twelve_months_amount": (
        "Revenue over the last twelve months of the filing in force, in US dollars, not adjusted for "
        "inflation. A rolling window that moves one quarter per filing. Empty when the filing reports no "
        "revenue. Used for price_to_sales_ratio; it never excludes a member from the index."
    ),
    "earnings_ten_year_average_amount": (
        "The member's average annual net income over its last up to 10 fiscal years, in US dollars of each "
        "year, NOT adjusted for inflation. A rolling window that moves one year per 10-K."
    ),
    "earnings_year_count": "Number of fiscal years behind the 10-year averages (up to 10). Fewer than 10 means a shorter window.",
    "filing_consumer_price_index_value": (
        "US consumer price index (index points) at the period end of the filing: the money the filing's "
        "inflation-adjusted average is expressed in."
    ),
    "consumer_price_index_value": "US consumer price index (index points) on valuation_date: today's money for the inflation adjustment.",
    "earnings_ten_year_average_inflation_adjusted_amount": (
        "The 10-year average earnings with every year converted into today's money: the filing's stored "
        "inflation-adjusted average x consumer_price_index_value / filing_consumer_price_index_value. US dollars. "
        "A rolling window. This is the earnings figure of the 10-year inflation-adjusted price/earnings ratio "
        "that the market climate valuation vote uses."
    ),
    "market_value_amount": "Market value of the member in US dollars: price_close x share_count. Empty without a price or a share count.",
    "is_used": (
        "True when the member counts in that day's index totals: it has a recent price, a filing with a share "
        "count, net income and both 10-year averages. Only used rows are in valuation_daily_index."
    ),
    "exclusion_reason_code": (
        "Why a member is not used, the first that applies: no_recent_price, no_filing, no_share_count, "
        "no_net_income, no_ten_year_average, no_consumer_price_index. Empty when used."
    ),
    "market_value_share_ratio": "Used members only: market_value_amount divided by the index market value of the day (0 to 1; the shares add up to 1).",
    "price_earnings_ten_year_average_inflation_adjusted_ratio": (
        "Used members only: the member's own price/earnings ratio on 10-year inflation-adjusted earnings "
        "(market_value_amount divided by earnings_ten_year_average_inflation_adjusted_amount). Empty when "
        "those earnings are not positive."
    ),
    "price_earnings_without_member_ratio": (
        "Used members only: what the index price/earnings ratio (10-year, inflation-adjusted) would be on that "
        "day without this member: (index market value minus the member's) divided by (index earnings minus the "
        "member's). Empty when the earnings left are not positive."
    ),
    "price_earnings_effect_ratio": (
        "Used members only: the index price/earnings ratio (10-year, inflation-adjusted) minus "
        "price_earnings_without_member_ratio. Positive: the member pushes the index ratio up (expensive for its "
        "earnings, or large). Negative: it pushes the ratio down. The effects of all members do not add up to "
        "the index ratio; they are one-at-a-time effects."
    ),
    "price_to_sales_ratio": (
        "Price over sales: market_value_amount divided by revenue_trailing_twelve_months_amount, on the same "
        "rolling twelve months of revenue and the day's price. A value of 15 means the market values the company "
        "at 15 times its yearly revenue. Empty when market value or revenue is missing or revenue is not above "
        "zero. Not limited to used members: a member left out of the index P/E can still have it."
    ),
    "currency_code": "Currency of the amounts: USD.",
    "ingested_timestamp": "Earliest fetch time of the price and filing rows behind this member and day.",
}

COLUMNS = [(f.name, f.dataType.simpleString()) for f in spark.sql(index_member_valuation_query()).schema.fields]


@dp.materialized_view(
    comment="Every current S&P 500 member on every valuation day: price, shares, earnings (trailing, 10-year, "
    "inflation-adjusted), whether it counts and why not, its share of the index market value and its effect on "
    "the index 10-year inflation-adjusted price/earnings ratio. One row per index, day and company; "
    "valuation_daily_index is the sum of its used rows.",
    schema=schema_with_comments(COLUMNS, COMMENTS),
)
def valuation_daily_index_member():
    return spark.sql(index_member_valuation_query())
