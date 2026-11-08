from common.strategy import (
    HALF_BAND,
    QUARTER_BAND,
    Week,
    bear_fund_band,
    bear_fund_setup,
    efficient_stock_passes,
    is_interim_entry,
    is_interim_watch,
    short_selling_entry,
    short_selling_setup,
)
from common.strategy_events_sql import reason_text_sql, strategy_events_query, strategy_states_query, week_complete


def week(close=100.0, previous=100.0, five=105.0, red=True, price_to_sales=None, down=0) -> Week:
    return Week(close, previous, five, red, price_to_sales, down)


def test_bear_fund_setup_needs_red_and_a_close_below_five_weeks_ago():
    assert bear_fund_setup(week())
    assert not bear_fund_setup(week(red=False))
    assert not bear_fund_setup(week(close=105.0))
    assert not bear_fund_setup(week(five=None))


def test_bear_fund_bands():
    assert bear_fund_band(week(close=94.0, previous=100.0)) == HALF_BAND
    assert bear_fund_band(week(close=96.9, previous=100.0)) == QUARTER_BAND
    assert bear_fund_band(week(close=98.0, previous=100.0)) is None
    assert bear_fund_band(week(close=94.0, previous=100.0, red=False)) is None


def test_the_interim_watch_is_a_small_fall_and_the_entry_a_further_drop():
    assert is_interim_watch(week(close=98.0, previous=100.0))
    assert not is_interim_watch(week(close=96.0, previous=100.0))
    assert not is_interim_watch(week(close=101.0, previous=100.0, five=105.0))
    assert is_interim_entry(98.0, 95.5)
    assert not is_interim_entry(98.0, 96.0)


def test_short_selling_setup_and_entry():
    assert short_selling_setup(week(price_to_sales=15.1, down=3))
    assert not short_selling_setup(week(price_to_sales=15.0, down=3))
    assert not short_selling_setup(week(price_to_sales=None, down=3))
    assert not short_selling_setup(week(price_to_sales=20, red=False, down=3))
    assert not short_selling_setup(week(price_to_sales=20, down=2))
    assert not short_selling_setup(week(price_to_sales=20, down=0))
    assert short_selling_entry(week(price_to_sales=20, down=6))
    assert not short_selling_entry(week(price_to_sales=20, down=7))
    assert not short_selling_entry(week(price_to_sales=5, down=6))
    assert not short_selling_entry(week(price_to_sales=20, down=5))


def test_efficient_stock_passes_on_tr60_and_volume_only():
    assert efficient_stock_passes(15.0, 200_001)
    assert not efficient_stock_passes(14.9, 5_000_000)
    assert not efficient_stock_passes(15.0, 200_000)
    assert not efficient_stock_passes(None, 5_000_000)
    assert not efficient_stock_passes(20.0, None)


def test_the_query_has_the_key_columns_the_events_and_the_thresholds():
    sql = strategy_events_query()
    for text in ("strategy_code", "trading_symbol_code", "event_date", "event_code", "setup_start_date", "entry_number",
                 "is_first_entry", "'^GSPC'", "monitor_code = 'market_climate'", "> 15", "= 6", "-0.025", "-0.05",
                 "lag(week_close, 5)", "'setup_start'", "'setup_end'", "'entry'", "s.down_weeks >= 3"):
        assert text in sql, text


def test_a_week_is_complete_on_its_friday_or_after_it_so_a_holiday_week_counts():
    assert week_complete("w") == (
        "(w.week_end_date = date_add(w.week_start, 4) OR current_date() > date_add(w.week_start, 4))"
    )
    assert "current_date()" in week_complete()


def test_the_reason_texts_name_both_strategies():
    assert reason_text_sql().count("WHEN") >= 6


def test_the_states_query_is_what_the_events_query_reads():
    states = strategy_states_query()
    for text in ("is_setup_on", "is_red", "down_week_count", "price_to_sales_ratio", "'bear_market_fund'", "'short_selling'"):
        assert text in states, text
    assert "setup_start" not in states and "entry_number" not in states
    assert strategy_states_query(domain="d", climate_source="c", member_source="m") in strategy_events_query(
        domain="d", climate_source="c", member_source="m"
    )
