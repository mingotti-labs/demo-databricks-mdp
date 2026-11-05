"""Currencies and rates of the Currency Monitor (openspec currency-monitor; story monitor-track-the-value-of-the-dollar).

One list drives the sources, the cross rates and the signals: a new currency is one entry in CURRENCIES and its
series in CURRENCY_RATES. Every exchange rate is turned into "the value of one unit in US dollars"; the value in
another base is that divided by the base's value in US dollars on the same day.
"""

from dataclasses import dataclass

MONITOR_CODE = "currency"
MONITOR_NAME = "Currency Monitor"
BASES = ["USD", "AUD"]
MAX_VALUE_AGE_DAYS = 10
STALE_AFTER_MONTHS = 4
YEAR_TRADING_DAYS = 252

DOLLAR_INDEX_SYMBOL = "DX-Y.NYB"
BROAD_INDEX_RATE_CODE = "us_dollar_broad_index"


@dataclass(frozen=True)
class Currency:
    """A main currency: its exchange-rate series and how it is quoted, and the rates of its country.

    `quote` is `usd_per_unit` (US dollars for one unit) or `units_per_usd` (units for one US dollar); the US dollar has no
    exchange rate. `short_rate_code` and `long_rate_code` are `rate_code`s of `market_rate_daily`; no 10-year when None.
    """

    code: str
    name: str
    exchange_rate_code: str | None
    quote: str | None
    short_rate_code: str
    long_rate_code: str | None


CURRENCIES = [
    Currency("USD", "US dollar", None, None, "us_federal_funds_effective_rate", "us_10_year_treasury_yield"),
    Currency("EUR", "Euro", "us_dollars_per_euro", "usd_per_unit", "euro_area_deposit_facility_rate", "euro_area_10_year_government_bond_yield"),
    Currency("JPY", "Japanese yen", "japanese_yen_per_us_dollar", "units_per_usd", "japan_3_month_interbank_rate", "japan_10_year_government_bond_yield"),
    Currency("GBP", "British pound", "us_dollars_per_british_pound", "usd_per_unit", "uk_call_money_rate", "uk_10_year_government_bond_yield"),
    Currency("CHF", "Swiss franc", "swiss_francs_per_us_dollar", "units_per_usd", "switzerland_3_month_interbank_rate", "switzerland_10_year_government_bond_yield"),
    Currency("CAD", "Canadian dollar", "canadian_dollars_per_us_dollar", "units_per_usd", "canada_3_month_interbank_rate", "canada_10_year_government_bond_yield"),
    Currency("SEK", "Swedish krona", "swedish_kronor_per_us_dollar", "units_per_usd", "sweden_3_month_interbank_rate", "sweden_10_year_government_bond_yield"),
    Currency("AUD", "Australian dollar", "us_dollars_per_australian_dollar", "usd_per_unit", "rba_cash_rate_target", "australia_10_year_government_bond_yield"),
    Currency("NZD", "New Zealand dollar", "us_dollars_per_new_zealand_dollar", "usd_per_unit", "new_zealand_3_month_interbank_rate", "new_zealand_10_year_government_bond_yield"),
    Currency("CNY", "Chinese yuan", "chinese_yuan_per_us_dollar", "units_per_usd", "china_3_month_interbank_rate", None),
]

# (rate_code, rate_name, source, series_id, unit) of the series added for the Currency Monitor.
CURRENCY_RATES = [
    ("us_dollars_per_euro", "US dollars per euro (FRED H.10)", "fred", "DEXUSEU", "us_dollars_per_euro"),
    ("japanese_yen_per_us_dollar", "Japanese yen per US dollar (FRED H.10)", "fred", "DEXJPUS", "japanese_yen_per_us_dollar"),
    ("us_dollars_per_british_pound", "US dollars per British pound (FRED H.10)", "fred", "DEXUSUK", "us_dollars_per_british_pound"),
    ("swiss_francs_per_us_dollar", "Swiss francs per US dollar (FRED H.10)", "fred", "DEXSZUS", "swiss_francs_per_us_dollar"),
    ("canadian_dollars_per_us_dollar", "Canadian dollars per US dollar (FRED H.10)", "fred", "DEXCAUS", "canadian_dollars_per_us_dollar"),
    ("swedish_kronor_per_us_dollar", "Swedish kronor per US dollar (FRED H.10)", "fred", "DEXSDUS", "swedish_kronor_per_us_dollar"),
    ("us_dollars_per_australian_dollar", "US dollars per Australian dollar (FRED H.10)", "fred", "DEXUSAL", "us_dollars_per_australian_dollar"),
    ("us_dollars_per_new_zealand_dollar", "US dollars per New Zealand dollar (FRED H.10)", "fred", "DEXUSNZ", "us_dollars_per_new_zealand_dollar"),
    ("chinese_yuan_per_us_dollar", "Chinese yuan per US dollar (FRED H.10)", "fred", "DEXCHUS", "chinese_yuan_per_us_dollar"),
    (BROAD_INDEX_RATE_CODE, "Nominal broad US dollar index (Federal Reserve, about 26 currencies by trade weight)", "fred", "DTWEXBGS", "index_points"),
    ("euro_area_deposit_facility_rate", "ECB deposit facility rate", "fred", "ECBDFR", "percent"),
    ("japan_3_month_interbank_rate", "Japan 3-month interbank rate (OECD)", "fred", "IR3TIB01JPM156N", "percent"),
    ("uk_call_money_rate", "UK call money interbank rate (OECD)", "fred", "IRSTCI01GBM156N", "percent"),
    ("switzerland_3_month_interbank_rate", "Switzerland 3-month interbank rate (OECD)", "fred", "IR3TIB01CHM156N", "percent"),
    ("canada_3_month_interbank_rate", "Canada 3-month interbank rate (OECD)", "fred", "IR3TIB01CAM156N", "percent"),
    ("sweden_3_month_interbank_rate", "Sweden 3-month interbank rate (OECD)", "fred", "IR3TIB01SEM156N", "percent"),
    ("new_zealand_3_month_interbank_rate", "New Zealand 3-month interbank rate (OECD)", "fred", "IR3TIB01NZM156N", "percent"),
    ("china_3_month_interbank_rate", "China 3-month interbank rate (OECD)", "fred", "IR3TIB01CNM156N", "percent"),
    ("euro_area_10_year_government_bond_yield", "Euro area 10-year government bond yield (OECD)", "fred", "IRLTLT01EZM156N", "percent"),
    ("japan_10_year_government_bond_yield", "Japan 10-year government bond yield (OECD)", "fred", "IRLTLT01JPM156N", "percent"),
    ("uk_10_year_government_bond_yield", "UK 10-year government bond yield (OECD)", "fred", "IRLTLT01GBM156N", "percent"),
    ("switzerland_10_year_government_bond_yield", "Switzerland 10-year government bond yield (OECD)", "fred", "IRLTLT01CHM156N", "percent"),
    ("canada_10_year_government_bond_yield", "Canada 10-year government bond yield (OECD)", "fred", "IRLTLT01CAM156N", "percent"),
    ("sweden_10_year_government_bond_yield", "Sweden 10-year government bond yield (OECD)", "fred", "IRLTLT01SEM156N", "percent"),
    ("new_zealand_10_year_government_bond_yield", "New Zealand 10-year government bond yield (OECD)", "fred", "IRLTLT01NZM156N", "percent"),
    ("australia_10_year_government_bond_yield", "Australia 10-year government bond yield (RBA)", "rba", "FCMYGBAG10D", "percent"),
]


def fred_series_ids() -> list[str]:
    """The FRED series ids of the Currency Monitor, in list order."""
    return [series_id for _, _, source, series_id, _ in CURRENCY_RATES if source == "fred"]


def value_in_us_dollars_sql(currency: Currency, rate_value: str = "rate_value") -> str:
    """SQL for the value of one unit of the currency in US dollars from its exchange rate."""
    if currency.quote == "usd_per_unit":
        return rate_value
    return f"1 / {rate_value}"


def other_currencies(base: str) -> list[Currency]:
    """The main currencies other than the base."""
    return [currency for currency in CURRENCIES if currency.code != base]


BASE_NAMES = {"USD": "US dollars", "AUD": "Australian dollars"}


def value_code(currency: str, base: str) -> str:
    """`rate_code` of the value of one unit of the currency in the base, for example currency_value_chf_in_aud."""
    return f"currency_value_{currency.lower()}_in_{base.lower()}"


def value_unit(base: str) -> str:
    return f"{BASE_NAMES[base].lower().replace(' ', '_')}_per_unit"


def value_series() -> list[tuple[Currency, str]]:
    """(currency, base) pairs that have a series: every main currency other than the base, for every base."""
    return [(currency, base) for base in BASES for currency in other_currencies(base)]


def exchange_rate_codes() -> list[str]:
    """`rate_code`s of the raw exchange rates the cross rates are built from."""
    return [c.exchange_rate_code for c in CURRENCIES if c.exchange_rate_code]


def carried_rate_codes() -> list[str]:
    """`rate_code`s of the rates and the broad index carried onto trading days as they are."""
    codes = [BROAD_INDEX_RATE_CODE]
    for currency in CURRENCIES:
        for code in (currency.short_rate_code, currency.long_rate_code):
            if code and code not in codes:
                codes.append(code)
    return codes
