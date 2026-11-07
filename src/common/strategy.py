"""Strategy rules (openspec strategy-events; stories strategy-001-bear market mutual fund and strategy-002-short selling).

The thresholds are the stories' own. The gold SQL reads these constants; the small functions are the reference the tests
check the rules against.
"""

from dataclasses import dataclass

BEAR_FUND_CODE = "bear_market_fund"
BEAR_FUND_NAME = "Bear market mutual fund"
SHORT_SELLING_CODE = "short_selling"
SHORT_SELLING_NAME = "Short selling"

SETUP_START = "setup_start"
ENTRY = "entry"
SETUP_END = "setup_end"
EVENTS = {SETUP_START: "Setup starts", ENTRY: "Entry", SETUP_END: "Setup ends"}

INDEX_SYMBOL = "^GSPC"
FIVE_WEEKS = 5
HALF_DROP_RATIO = -0.05
QUARTER_DROP_RATIO = -0.025
INTERIM_DAYS = (0, 1, 2)  # Monday, Tuesday, Wednesday of the week after the watch week, as days after its Monday
PRICE_TO_SALES_MIN = 15
DOWN_WEEKS_FOR_ENTRY = 6

HALF_BAND = "half_of_equity"
QUARTER_BAND = "quarter_of_equity"
INTERIM_BAND = "interim_quarter_of_equity"


@dataclass(frozen=True)
class Week:
    """One Monday-based week of a listing: its close, the closes before it, and the climate and price/sales that day."""

    close: float
    previous_close: float | None
    five_weeks_close: float | None
    is_red: bool
    price_to_sales: float | None = None
    down_weeks: int = 0


def bear_fund_setup(week: Week) -> bool:
    """Any climate light red and the close lower than five weeks earlier."""
    return week.is_red and week.five_weeks_close is not None and week.close < week.five_weeks_close


def bear_fund_band(week: Week) -> str | None:
    """The entry band of a setup week: at most -5% half of equity, at most -2.5% a quarter."""
    if not bear_fund_setup(week) or week.previous_close is None:
        return None
    change = week.close / week.previous_close - 1
    if change <= HALF_DROP_RATIO:
        return HALF_BAND
    if change <= QUARTER_DROP_RATIO:
        return QUARTER_BAND
    return None


def is_interim_watch(week: Week) -> bool:
    """A setup week that fell, but by less than 2.5%: Monday to Wednesday of the next week can still trigger an entry."""
    if not bear_fund_setup(week) or week.previous_close is None:
        return False
    change = week.close / week.previous_close - 1
    return QUARTER_DROP_RATIO < change < 0


def is_interim_entry(watch_close: float, day_close: float) -> bool:
    """A close at least 2.5% below the watch week's close."""
    return day_close / watch_close - 1 <= QUARTER_DROP_RATIO


def short_selling_setup(week: Week) -> bool:
    """Any climate light red and price-to-sales above 15 (empty price-to-sales never sets up)."""
    return week.is_red and week.price_to_sales is not None and week.price_to_sales > PRICE_TO_SALES_MIN


def short_selling_entry(week: Week) -> bool:
    """The week the streak of weekly closes down reaches six, with the setup on."""
    return short_selling_setup(week) and week.down_weeks == DOWN_WEEKS_FOR_ENTRY


def events_values_sql() -> str:
    """VALUES rows (event_code, event_name)."""
    return ", ".join(f"('{code}', '{name}')" for code, name in EVENTS.items())
