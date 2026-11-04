from datetime import date

from common.market_climate import (
    LENSES,
    add_months,
    climate,
    fed_in_the_way,
    lenses_values_sql,
    lights_values_sql,
    market_going_up,
    too_expensive,
)

LONG_RUN, MODERN = LENSES


def test_the_same_pe_can_be_expensive_for_one_lens_only():
    assert too_expensive(27.4, LONG_RUN) == (True, "red")
    assert too_expensive(27.4, MODERN) == (False, "yellow")


def test_valuation_bands_follow_the_lines():
    assert too_expensive(15.9, LONG_RUN) == (False, "green")
    assert too_expensive(22.0, LONG_RUN) == (False, "yellow")
    assert too_expensive(22.1, LONG_RUN) == (True, "red")
    assert too_expensive(21.9, MODERN) == (False, "green")
    assert too_expensive(22.0, MODERN) == (False, "yellow")
    assert too_expensive(30.1, MODERN) == (True, "red")


def test_market_going_up_is_yes_above_the_average_and_the_band_follows_the_slope():
    assert market_going_up(7568.9, 7315.9, 0.011) == (True, "green")
    assert market_going_up(7568.9, 7315.9, 0.001) == (True, "yellow")
    assert market_going_up(7568.9, 7315.9, -0.01) == (True, "yellow")
    assert market_going_up(7568.9, 7315.9, None) == (True, "yellow")
    assert market_going_up(7000.0, 7315.9, 0.02) == (False, "red")
    assert market_going_up(7315.9, 7315.9, 0.02) == (False, "red")


def test_add_months_clamps_to_the_month_end():
    assert add_months(date(2023, 7, 27), 6) == date(2024, 1, 27)
    assert add_months(date(2023, 8, 31), 6) == date(2024, 2, 29)
    assert add_months(date(2024, 12, 15), 6) == date(2025, 6, 15)


def test_a_hike_counts_for_six_months_then_stops():
    changes = [(date(2023, 7, 27), 5.25, 5.5), (date(2024, 9, 19), 5.5, 5.0)]
    assert fed_in_the_way(changes, date(2023, 7, 27)) == (True, "red")
    assert fed_in_the_way(changes, date(2024, 1, 26)) == (True, "red")
    assert fed_in_the_way(changes, date(2024, 1, 27)) == (False, "yellow")


def test_a_cut_ends_the_window_at_once_and_is_green_for_six_months():
    changes = [(date(2023, 7, 27), 5.25, 5.5), (date(2023, 9, 1), 5.5, 5.25)]
    assert fed_in_the_way(changes, date(2023, 9, 1)) == (False, "green")
    assert fed_in_the_way(changes, date(2024, 3, 1)) == (False, "yellow")


def test_a_new_hike_restarts_the_six_months():
    changes = [(date(2023, 1, 5), 4.0, 4.25), (date(2023, 5, 10), 4.25, 4.5)]
    assert fed_in_the_way(changes, date(2023, 7, 10)) == (True, "red")
    assert fed_in_the_way(changes, date(2023, 11, 9)) == (True, "red")
    assert fed_in_the_way(changes, date(2023, 11, 10)) == (False, "yellow")


def test_before_any_known_change_the_fed_is_not_in_the_way():
    assert fed_in_the_way([(date(2008, 12, 16), 1.0, 0.25)], date(2008, 12, 1)) == (False, "yellow")


def test_climate_is_red_for_two_or_three_yes_answers():
    assert climate([True, False, True]) == (2, "red", "sell")
    assert climate([True, True, True]) == (3, "red", "sell")
    assert climate([False, True, False]) == (1, "yellow", "buy and hold")
    assert climate([False, False, False]) == (0, "green", "strong buy")


def test_story_example_two_lenses_two_lights():
    """P/E 27.4, last Fed change a cut, S&P 500 above its average: long run red, modern yellow."""
    fed_yes, _ = fed_in_the_way([(date(2025, 12, 10), 4.0, 3.75)], date(2026, 11, 3))
    trend_yes, _ = market_going_up(7568.9, 7315.9, 0.011)
    long_run = climate([too_expensive(27.4, LONG_RUN)[0], fed_yes, trend_yes])
    modern = climate([too_expensive(27.4, MODERN)[0], fed_yes, trend_yes])
    assert long_run == (2, "red", "sell")
    assert modern == (1, "yellow", "buy and hold")


def test_sql_helpers_list_every_light_and_lens():
    assert lights_values_sql().count("(") == 4
    assert "'Market climate long run'" in lenses_values_sql()
    assert "'Market climate modern'" in lenses_values_sql()
