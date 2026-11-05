## MODIFIED Requirements

### Requirement: Market rates
`market_rate_daily` SHALL have one row per rate and date for the Australian
dollar in US dollars (RBA `FXRUSD`), the RBA cash rate target (`FIRMMCRTD`), the
US 10-year Treasury yield (`DGS10`), the effective federal funds rate (`DFF`)
the Fed target range limits (`DFEDTARU`, `DFEDTARL`), the nine FRED exchange rates of the Currency Monitor,
the ECB deposit facility rate, the OECD short-term and long-term rates of the FRED fetch and the Australian
10-year government bond yield (RBA `FCMYGBAG10D`), with a `rate_code`
(`australian_dollar_in_us_dollars`, `rba_cash_rate_target`,
`us_10_year_treasury_yield`, `us_federal_funds_effective_rate`,
`us_federal_funds_target_upper`, `us_federal_funds_target_lower`, and one code per added series, named for
what it is, for example `swiss_francs_per_us_dollar`, `us_dollars_per_euro`, `japan_short_term_interest_rate`,
`switzerland_10_year_government_bond_yield`), `rate_name`,
`observation_date`, `rate_value`, `unit_name`, `source_system_code`,
`source_series_id` and `is_carried_forward`. `is_carried_forward` SHALL be false
on these rows.

It SHALL also have one row per business day (Monday to Friday) for each CPI series,
with `unit_name` `index_points` and `rate_code` `au_cpi_all_groups_monthly`,
`au_cpi_all_groups_quarterly`, `us_cpi_all_items_not_seasonally_adjusted`,
`us_cpi_all_items_seasonally_adjusted` or
`us_cpi_excluding_food_and_energy_seasonally_adjusted`. A CPI value SHALL start on the
first business day on or after the first day of its period and repeat on each business
day until the next period starts, and the last value SHALL repeat up to the latest date
of the other rates. Rows after a period's first business day SHALL have
`is_carried_forward` true. Only current versions of ABS rows SHALL be used.

#### Scenario: The latest cash rate
- **WHEN** RBA's latest cash rate target is 4.60
- **THEN** `market_rate_daily` has that value under the cash rate's `rate_code` on its
  date

#### Scenario: A monthly CPI value
- **WHEN** ABS monthly CPI for `2026-09` is 104.34 and no later month exists
- **THEN** `au_cpi_all_groups_monthly` has 104.34 on 2026-09-01 with `is_carried_forward`
  false, and on every later business day up to the latest date of the other rates with
  `is_carried_forward` true

#### Scenario: A quarterly CPI value
- **WHEN** ABS quarterly CPI for `2026-Q3` is 103.64
- **THEN** `au_cpi_all_groups_quarterly` holds 103.64 from 2026-07-01 (a Wednesday) through
  the day before the next value starts

#### Scenario: Weekends
- **WHEN** a period starts on a Saturday
- **THEN** its first row is the next Monday and no CPI row has a Saturday or Sunday date

#### Scenario: A monthly OECD rate
- **WHEN** FRED's `IRSTCI01GBM156N` has 3.7305 for 2026-09-01
- **THEN** `market_rate_daily` has 3.7305 under the UK short-term rate's `rate_code` on 2026-09-01, and no
  carried rows (the carrying happens in `market_rate_indicator_daily`)

### Requirement: Market rate indicators
`market_rate_indicator_daily` SHALL have one row per `rate_code` and `indicator_date` for every `^GSPC` price
date, for `us_cpi_all_items_not_seasonally_adjusted` (the CPI index), `us_federal_funds_effective_rate`,
`us_cpi_change_previous_reading_percent`,
`us_cpi_change_twelve_months_percent` and `us_real_federal_funds_rate`, for the short-term and 10-year rates
of the Currency Monitor, and for the value of each main currency in US dollars and in Australian dollars
(`currency_value_<code>_in_usd`, `currency_value_<code>_in_aud`), with `rate_name`, `rate_value` (the
latest value of the series on or before the date: index points for the CPI index, percent for the others), `two_hundred_day_average_value` (the average of
the series' last 200 rows, empty when fewer exist), `two_hundred_day_average_change_value` (that average minus
the same average 20 rows earlier), `day_count`, `is_calculated`, `unit_name` and `ingested_timestamp`. The CPI
changes SHALL be worked out on the monthly readings of `us_cpi_all_items_not_seasonally_adjusted` and carried to
every date until the next reading; the real rate SHALL be the effective rate minus the CPI 12-month change of
the same date. Every column SHALL carry a Unity Catalog description.

#### Scenario: A month of CPI
- **WHEN** the CPI of September is 336.94 and of August 334.98
- **THEN** every date from the September reading until the October reading has
  `us_cpi_change_previous_reading_percent` 0.585 (rounded)

#### Scenario: The real rate
- **WHEN** on a date the effective rate is 4.10 and the CPI 12-month change is 3.00
- **THEN** `us_real_federal_funds_rate` on that date is 1.10
The value of a currency in US dollars SHALL be its FRED exchange rate when quoted as US dollars per unit and
one divided by it when quoted as units per US dollar; its value in Australian dollars SHALL be its value in
US dollars divided by the value of one Australian dollar in US dollars on the same date. One list of
currencies and bases SHALL drive these series. The inflation series SHALL not change.

#### Scenario: Swiss franc in Australian dollars
- **WHEN** on a date FRED quotes 0.8230 Swiss francs per US dollar and 0.7038 US dollars per Australian dollar
- **THEN** `currency_value_chf_in_usd` is 1.2151 and `currency_value_chf_in_aud` is 1.7264 (rounded)
