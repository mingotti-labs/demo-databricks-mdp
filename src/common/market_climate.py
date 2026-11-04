"""Market climate rules (openspec market-climate-gold; story monitor-understand-market-climate).

The thresholds are hard-coded on purpose (user, 2026-11-04). The gold SQL reads these constants; the
small functions are the reference the tests check the rules against.
"""

from dataclasses import dataclass
from datetime import date

MONITOR_CODE = "market_climate"
MONITOR_NAME = "Market climate"
INDEX_CODE = "SP500"

FED_WINDOW_MONTHS = 6
FED_MAX_LAG_DAYS = 7
TREND_FLAT_SLOPE = 0.002
PRICE_MAX_AGE_DAYS = 5
LISTING_VOLUME_WINDOW_ROWS = 60


@dataclass(frozen=True)
class Lens:
    """A valuation lens: the P/E above which the market counts as too expensive, and its bands."""

    code: str
    name: str
    expensive_line: int
    cheap_line: int


LENSES = [
    Lens("long_run", "Market climate long run", expensive_line=22, cheap_line=16),
    Lens("modern", "Market climate modern", expensive_line=30, cheap_line=22),
]

# Yes answers -> (light, action). Two or three yes answers are red.
LIGHTS = {0: ("green", "strong buy"), 1: ("yellow", "buy and hold"), 2: ("red", "sell"), 3: ("red", "sell")}


def too_expensive(ratio: float, lens: Lens) -> tuple[bool, str]:
    """(is_yes, band) for a 10-year inflation-adjusted P/E: green below the cheap line, red above the expensive one."""
    band = "green" if ratio < lens.cheap_line else "yellow" if ratio <= lens.expensive_line else "red"
    return ratio > lens.expensive_line, band


def market_going_up(close: float, average: float, slope: float | None) -> tuple[bool, str]:
    """(is_yes, band): yes when the close is above its 200-day average (the unfavourable answer)."""
    if close <= average:
        return False, "red"
    return True, "green" if slope is not None and slope >= TREND_FLAT_SLOPE else "yellow"


def add_months(day: date, months: int) -> date:
    """`day` plus whole months, clamped to the month's last day (as Spark's add_months)."""
    month_index = day.month - 1 + months
    year, month = day.year + month_index // 12, month_index % 12 + 1
    last = [31, 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    return date(year, month, min(day.day, last))


def fed_in_the_way(changes: list[tuple[date, float, float]], day: date) -> tuple[bool, str]:
    """(is_yes, band) from the Fed target changes (change date, rate before, rate after).

    Yes when the latest change on or before `day` was a hike made less than six months earlier. Band red
    when yes, green after a cut less than six months old, yellow otherwise.
    """
    known = [change for change in changes if change[0] <= day]
    if not known:
        return False, "yellow"
    changed_on, before, after = max(known)
    recent = day < add_months(changed_on, FED_WINDOW_MONTHS)
    if after > before:
        return recent, "red" if recent else "yellow"
    return False, "green" if recent else "yellow"


def climate(answers_yes: list[bool]) -> tuple[int, str, str]:
    """(yes count, light, action) of a lens's three answers."""
    count = sum(answers_yes)
    light, action = LIGHTS[count]
    return count, light, action


def lights_values_sql() -> str:
    """VALUES rows (yes_count, light, action) to join the climate result."""
    return ", ".join(f"({count}, '{light}', '{action}')" for count, (light, action) in LIGHTS.items())


def lenses_values_sql() -> str:
    """VALUES rows (lens_code, lens_name, expensive_line, cheap_line)."""
    return ", ".join(f"('{l.code}', '{l.name}', {l.expensive_line}, {l.cheap_line})" for l in LENSES)
