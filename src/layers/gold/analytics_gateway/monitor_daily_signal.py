# Gold analytics gateway: monitor_daily_signal (openspec market-climate-gold, market-climate-dashboard). One long table for every
# monitoring story: a row per day, monitor, lens and signal. The market climate writes three yes/no
# answers and a result per lens (common/market_climate_signals_sql.py); the inflation/deflation monitor
# writes four stars and a rating (common/inflation_signals_sql.py, openspec inflation-deflation-monitor).
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.inflation_signals_sql import inflation_signal_query  # noqa: E402
from common.investments import schema_with_comments  # noqa: E402
from common.market_climate_signals_sql import monitor_signal_query  # noqa: E402
from common.market_climate_sql import index_member_valuation_query, index_valuation_query  # noqa: E402

COMMENTS = {
    "signal_date": "Trading day the signal is as of (point in time).",
    "monitor_code": "Which monitoring story the row belongs to: market_climate (the market climate lights) or inflation_deflation "
        "(the inflation/deflation stars and rating). More monitors add rows here.",
    "monitor_name": "Display name of the monitor.",
    "lens_code": (
        "Reading of the monitor. Market climate has two lenses that differ only in the valuation line: "
        "long_run (too expensive above a price/earnings ratio of 22) and modern (above 30). Inflation/deflation "
        "has one lens, game_plan."
    ),
    "lens_name": (
        "Display name of the lens; on the market climate result row it is Market climate long run or Market climate "
        "modern; for inflation/deflation it is Inflation/deflation game plan."
    ),
    "signal_code": (
        "Market climate: too_expensive, fed_in_the_way or market_going_up (the three yes/no answers), or climate (the "
        "result of the lens: its light). Inflation/deflation: commodity_prices, consumer_prices, gold_prices or "
        "interest_rates (the four stars), or rating (the result)."
    ),
    "signal_name": "Display name of the signal.",
    "is_yes": (
        "The answer to the question: true is yes. Inflation/deflation star rows: true means the star is on (the "
        "indicator points to inflation). Market climate: yes is the unfavourable answer for all three questions "
        "(market too expensive, Fed in the way, market going up, because the efficient and undervalued "
        "strategies find their signals when the market is below its 200-day average). Empty on result rows (climate, rating)."
    ),
    "band_code": (
        "green, yellow or red. On an answer row, a finer reading used for drilldown (valuation: green below "
        "the cheap line, yellow up to the expensive line, red above; Fed: red during six months after a hike, "
        "green during six months after a cut, else yellow; trend: red at or below the 200-day average, green "
        "above it with a rising average, else yellow). On a climate row, the light: red for 2 or 3 yes answers "
        "(sell), yellow for 1 (buy and hold), green for none (strong buy). Inflation/deflation: a star row is red when "
        "the star is on, green when off; the rating row is red for 3 or 4 stars, yellow for 2, green for 0 or 1, "
        "blue for -1 (deflation)."
    ),
    "measured_value": (
        "What was measured: the 10-year inflation-adjusted price/earnings ratio (too_expensive), the Fed target "
        "rate upper limit in percent (fed_in_the_way), or the S&P 500 adjusted close (market_going_up); commodity_prices: the 20-day change of the CRB index "
        "200-day average as a ratio (0.03 is 3%); consumer_prices: the 20-day change of the CPI index 200-day "
        "average in index points; gold_prices: the gold futures close; interest_rates: the federal funds effective "
        "rate in percent; rating: the rating from -1 to 4. Empty on climate rows."
    ),
    "threshold_value": (
        "What it was compared with: the valuation line (22 or 30), the Fed target before its latest change, "
        "or the 200-day average of the S&P 500 close; commodity_prices and consumer_prices: 0; gold_prices and "
        "interest_rates: the 200-day average; rating: the US CPI change over 12 months in percent. Empty on climate rows."
    ),
    "reason_text": "One plain sentence saying what was measured and why the answer or light is what it is.",
    "yes_count": (
        "Result rows only: climate, how many of the lens's three answers are yes (0 to 3); rating, how many of "
        "the four stars are on (0 to 4)."
    ),
    "action_name": (
        "Result rows only: climate, the action the light stands for: sell (red), buy and hold (yellow), strong buy "
        "(green); rating, its label: Increasing Inflation (4 stars), Inflation Danger (3), Some Inflation Risk (2), "
        "Mild or Decreasing Inflation (1), Decreasing Inflation (0), Deflation (-1: no star on and US consumer "
        "prices below their level 12 months earlier)."
    ),
    "ingested_timestamp": "Earliest fetch time of the input rows behind the signal.",
}


def all_signals_query(valuation_source: str = "valuation_daily_index") -> str:
    """The rows of every monitor: market climate and inflation/deflation."""
    return f"SELECT * FROM ({monitor_signal_query(valuation_source)}) UNION ALL SELECT * FROM ({inflation_signal_query()})"


COLUMNS = [
    (f.name, f.dataType.simpleString())
    for f in spark.sql(
        all_signals_query(f"({index_valuation_query(f'({index_member_valuation_query()})')})")
    ).schema.fields
]


@dp.materialized_view(
    comment="Signals of the monitoring stories, one row per day, monitor, lens and signal. Market climate: three "
    "yes/no answers (too expensive, Fed in the way, market going up) and the resulting light per lens. "
    "Inflation/deflation: four stars (commodity prices, consumer prices, gold prices, interest rates) and the rating.",
    schema=schema_with_comments(COLUMNS, COMMENTS),
)
def monitor_daily_signal():
    return spark.sql(all_signals_query())
