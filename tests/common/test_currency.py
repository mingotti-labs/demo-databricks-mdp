from common.currency import (
    BASES,
    CURRENCIES,
    CURRENCY_RATES,
    fred_series_ids,
    other_currencies,
    value_in_us_dollars_sql,
)
from common.investments import CPI_RATES, RATES, rate_values_sql


def test_currency_rate_codes_are_unique_and_do_not_overlap_other_rates():
    codes = [code for code, *_ in CURRENCY_RATES]
    assert len(codes) == len(set(codes))
    assert not set(codes) & {code for code, *_ in RATES}
    assert not set(codes) & {code for code, *_ in CPI_RATES}


def test_every_currency_points_at_series_that_exist():
    codes = {code for code, *_ in CURRENCY_RATES} | {code for code, *_ in RATES}
    for currency in CURRENCIES:
        for rate_code in (currency.exchange_rate_code, currency.short_rate_code, currency.long_rate_code):
            assert rate_code is None or rate_code in codes, (currency.code, rate_code)
    assert all(c.exchange_rate_code or c.code == "USD" for c in CURRENCIES)


def test_the_dollar_index_currencies_and_the_user_choices_are_all_there():
    assert [c.code for c in CURRENCIES] == ["USD", "EUR", "JPY", "GBP", "CHF", "CAD", "SEK", "AUD", "NZD", "CNY"]
    assert BASES == ["USD", "AUD"]
    assert [c.code for c in other_currencies("AUD")][:2] == ["USD", "EUR"]
    assert "AUD" not in [c.code for c in other_currencies("AUD")]


def test_only_china_has_no_ten_year_yield():
    assert [c.code for c in CURRENCIES if c.long_rate_code is None] == ["CNY"]


def test_value_in_us_dollars_for_both_quotes():
    by_code = {c.code: c for c in CURRENCIES}
    assert value_in_us_dollars_sql(by_code["EUR"]) == "rate_value"
    assert value_in_us_dollars_sql(by_code["CHF"]) == "1 / rate_value"
    assert value_in_us_dollars_sql(by_code["CHF"], "r.value") == "1 / r.value"


def test_chf_in_aud_example_of_the_spec():
    chf_per_usd, usd_per_aud = 0.8230, 0.7038
    in_usd = 1 / chf_per_usd
    assert round(in_usd, 4) == 1.2151
    assert round(in_usd / usd_per_aud, 4) == 1.7264


def test_fred_series_are_unique_and_include_the_broad_index():
    ids = fred_series_ids()
    assert len(ids) == len(set(ids)) == 25
    assert "DTWEXBGS" in ids and "DEXSDUS" in ids


def test_rate_values_sql_lists_the_currency_series_too():
    sql = rate_values_sql()
    assert "'swiss_francs_per_us_dollar'" in sql and "'australia_10_year_government_bond_yield'" in sql
    assert "'rba_cash_rate_target'" in sql
