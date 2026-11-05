"""Inflation/deflation rules (openspec inflation-deflation-monitor; story monitor-inflation-deflation-game-plan).

The gold SQL reads these constants; the small functions are the reference the tests check the rules against.
"""

MONITOR_CODE = "inflation_deflation"
MONITOR_NAME = "Inflation deflation"
LENS_CODE = "game_plan"
LENS_NAME = "Inflation/deflation game plan"

MAX_LAG_DAYS = 7
COMMODITY_SYMBOL = "^TRCCRB"
GOLD_SYMBOL = "GC=F"
STAR_COUNT = 4

# Stars on -> (band, label); -1 is deflation.
RATINGS = {
    4: ("red", "Increasing Inflation"),
    3: ("red", "Inflation Danger"),
    2: ("yellow", "Some Inflation Risk"),
    1: ("green", "Mild or Decreasing Inflation"),
    0: ("green", "Decreasing Inflation"),
    -1: ("blue", "Deflation"),
}


def rating(stars_on: int, cpi_twelve_month_change: float) -> int:
    """The stars on (0 to 4), or -1 when none is on and prices are lower than a year ago."""
    return -1 if stars_on == 0 and cpi_twelve_month_change < 0 else stars_on


def ratings_values_sql() -> str:
    """The `VALUES` rows (rating, band, label) for the SQL."""
    return ", ".join(f"({value}, '{band}', '{label}')" for value, (band, label) in RATINGS.items())
