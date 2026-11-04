# Gold analytics gateway: monitor_daily_signal (openspec market-climate-gold, market-climate-dashboard). One long table for every
# monitoring story: a row per day, monitor, lens and signal. The market climate writes three yes/no
# answers and a result per lens. The query is in common/market_climate_signals_sql.py.
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.investments import schema_with_comments  # noqa: E402
from common.market_climate_signals_sql import monitor_signal_query  # noqa: E402
from common.market_climate_sql import index_member_valuation_query, index_valuation_query  # noqa: E402

COMMENTS = {
    "signal_date": "Trading day the signal is as of (point in time).",
    "monitor_code": "Which monitoring story the row belongs to; market_climate for the market climate (more monitors add rows here).",
    "monitor_name": "Display name of the monitor.",
    "lens_code": (
        "Reading of the monitor. Market climate has two lenses that differ only in the valuation line: "
        "long_run (too expensive above a price/earnings ratio of 22) and modern (above 30)."
    ),
    "lens_name": "Display name of the lens; on the climate row it is Market climate long run or Market climate modern.",
    "signal_code": (
        "too_expensive, fed_in_the_way or market_going_up (the three yes/no answers), or climate (the result "
        "of the lens: its light)."
    ),
    "signal_name": "Display name of the signal.",
    "is_yes": (
        "The answer to the question: true is yes. Yes is the unfavourable answer for all three questions "
        "(market too expensive, Fed in the way, market going up, because the efficient and undervalued "
        "strategies find their signals when the market is below its 200-day average). Empty on climate rows."
    ),
    "band_code": (
        "green, yellow or red. On an answer row, a finer reading used for drilldown (valuation: green below "
        "the cheap line, yellow up to the expensive line, red above; Fed: red during six months after a hike, "
        "green during six months after a cut, else yellow; trend: red at or below the 200-day average, green "
        "above it with a rising average, else yellow). On a climate row, the light: red for 2 or 3 yes answers "
        "(sell), yellow for 1 (buy and hold), green for none (strong buy)."
    ),
    "measured_value": (
        "What was measured: the 10-year inflation-adjusted price/earnings ratio (too_expensive), the Fed target "
        "rate upper limit in percent (fed_in_the_way), or the S&P 500 adjusted close (market_going_up). "
        "Empty on climate rows."
    ),
    "threshold_value": (
        "What it was compared with: the valuation line (22 or 30), the Fed target before its latest change, "
        "or the 200-day average of the S&P 500 close. Empty on climate rows."
    ),
    "reason_text": "One plain sentence saying what was measured and why the answer or light is what it is.",
    "yes_count": "Climate rows only: how many of the lens's three answers are yes (0 to 3).",
    "action_name": "Climate rows only: the action the light stands for: sell (red), buy and hold (yellow), strong buy (green).",
    "ingested_timestamp": "Earliest fetch time of the input rows behind the signal.",
}

COLUMNS = [
    (f.name, f.dataType.simpleString())
    for f in spark.sql(
        monitor_signal_query(f"({index_valuation_query(f'({index_member_valuation_query()})')})")
    ).schema.fields
]


@dp.materialized_view(
    comment="Signals of the monitoring stories, one row per day, monitor, lens and signal. Market climate: three "
    "yes/no answers (too expensive, Fed in the way, market going up) and the resulting light per lens.",
    schema=schema_with_comments(COLUMNS, COMMENTS),
)
def monitor_daily_signal():
    return spark.sql(monitor_signal_query())
