# Gold analytics gateway: strategy_daily_event (openspec strategy-events). One row per strategy, symbol, day and event,
# only when something happens: a setup starts, an entry rule fires, a setup ends. Strategy 001 (bear market mutual fund)
# runs on the S&P 500, strategy 002 (short selling) on the index members. The query is in common/strategy_events_sql.py
# so a probe can run the same text.
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.investments import schema_with_comments  # noqa: E402
from common.market_climate_signals_sql import monitor_signal_query  # noqa: E402
from common.market_climate_sql import index_member_valuation_query, index_valuation_query  # noqa: E402
from common.strategy_events_sql import strategy_events_query  # noqa: E402

COMMENTS = {
    "strategy_code": (
        "Which strategy the event belongs to: bear_market_fund (strategy 001, buy a bear fund when the market climate is "
        "red and the S&P 500 keeps falling) or short_selling (strategy 002, short expensive stocks that keep falling)."
    ),
    "strategy_name": "Display name of the strategy.",
    "trading_symbol_code": (
        "Symbol the event is about: ^GSPC (the S&P 500 index) for bear_market_fund, the stock's trading symbol for "
        "short_selling. Joins to silver_domain_investments.listing and price_daily on trading_symbol_code."
    ),
    "event_date": (
        "Day of the event. Setup and entry events from a week are dated on the week's last trading day (a Friday, or the "
        "Thursday before a holiday Friday); an interim entry (entry_band_code interim_quarter_of_equity) is dated on the "
        "Monday, Tuesday or Wednesday it happened. Only complete weeks are evaluated, and only from the first day the "
        "market climate exists (2025-10-29)."
    ),
    "event_code": (
        "setup_start: the first week the strategy's setup conditions are all true; entry: an entry rule fired while the "
        "setup is on; setup_end: the first week the setup is no longer true. A setup period runs from its setup_start "
        "to its setup_end; a period that has no setup_end yet is still on."
    ),
    "event_name": "Display name of the event: Setup starts, Entry or Setup ends.",
    "listing_id": "The listing of the symbol (hash of market and symbol). Joins to silver_domain_investments.listing.listing_id and price_daily.listing_id.",
    "setup_start_date": (
        "The event_date of the setup_start that opened the setup period this row belongs to. Every event of one setup "
        "period (its start, its entries and its end) has the same value: use it to group a period or to pick a past one."
    ),
    "entry_number": "Entry rows only: 1 for the first entry of the setup period, 2 for the second, and so on, by date.",
    "is_first_entry": "Entry rows only: true for the first entry of the setup period. Empty on setup rows.",
    "entry_band_code": (
        "Strategy 001 entry rows only: how much of account equity to invest in the bear fund. half_of_equity: the S&P 500 "
        "fell 5% or more over the week; quarter_of_equity: it fell 2.5% to 5%; interim_quarter_of_equity: the week fell by "
        "less than 2.5% but a close on the following Monday, Tuesday or Wednesday was at least 2.5% below that week's close. "
        "Empty for strategy 002 and for setup rows."
    ),
    "week_close_amount": (
        "Close of the symbol on the week's last trading day: the S&P 500 index level for strategy 001, the stock's "
        "split-adjusted close in US dollars for strategy 002. The week is Monday to Friday."
    ),
    "five_weeks_close_amount": (
        "Strategy 001 only: the S&P 500 close of the week five weeks earlier. The setup needs week_close_amount below it. "
        "Empty for strategy 002."
    ),
    "week_change_ratio": (
        "Close of the week divided by the close of the previous week, minus 1 (-0.031 is a fall of 3.1%). Rolling over "
        "complete weeks. Strategy 001 uses it for the entry bands."
    ),
    "price_to_sales_ratio": (
        "Strategy 002 only: the stock's price over sales that day (market value over trailing twelve months revenue, from "
        "valuation_daily_index_member). The setup needs it above 15. Empty for strategy 001."
    ),
    "down_week_count": (
        "Strategy 002 only: how many weeks in a row the stock's weekly close has been below the previous week's, up to "
        "this week. The entry fires the week it reaches 6. Empty for strategy 001."
    ),
    "reason_text": "One plain sentence saying why the event happened.",
    "currency_code": "Currency of the amounts: USD.",
    "ingested_timestamp": "Earliest fetch time of the price rows behind the event.",
}

# The output columns come from the query run on inline sources (the sibling tables do not exist yet at import).
_members = "(" + index_member_valuation_query() + ")"
_valuation = "(" + index_valuation_query(_members) + ")"
_climate = "(" + monitor_signal_query(_valuation) + ")"
COLUMNS = [
    (f.name, f.dataType.simpleString())
    for f in spark.sql(strategy_events_query(climate_source=_climate, member_source=_members)).schema.fields
]


@dp.materialized_view(
    comment="Events of strategy 001 (bear market mutual fund, on the S&P 500) and strategy 002 (short selling, on the "
    "index members): one row per strategy, symbol, day and event (setup_start, entry, setup_end), only when something "
    "happens. Weekly rules worked out from daily prices; the market climate gates both strategies.",
    schema=schema_with_comments(COLUMNS, COMMENTS),
)
def strategy_daily_event():
    return spark.sql(strategy_events_query())
