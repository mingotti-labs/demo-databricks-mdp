## MODIFIED Requirements

### Requirement: Market rates
`market_rate_daily` SHALL have one row per rate and date for the Australian
dollar in US dollars (RBA `FXRUSD`), the RBA cash rate target (`FIRMMCRTD`), the
US 10-year Treasury yield (`DGS10`), the US 3-month, 1-year, 2-year and 3-year Treasury yields (`DGS3MO`, `DGS1`,
`DGS2`, `DGS3`), the effective federal funds rate (`DFF`)
the Fed target range limits (`DFEDTARU`, `DFEDTARL`), the nine FRED exchange rates of the Currency Monitor,
the ECB deposit facility rate, the OECD short-term and long-term rates of the FRED fetch and the Australian
10-year government bond yield (RBA `FCMYGBAG10D`), with a `rate_code`
(`australian_dollar_in_us_dollars`, `rba_cash_rate_target`,
`us_10_year_treasury_yield`, `us_3_month_treasury_yield`, `us_1_year_treasury_yield`, `us_2_year_treasury_yield`,
`us_3_year_treasury_yield`, `us_federal_funds_effective_rate`,
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

#### Scenario: The short-term US yields
- **WHEN** FRED's `DGS2` is 4.46 on 2026-11-05
- **THEN** `market_rate_daily` has 4.46 under `us_2_year_treasury_yield` on 2026-11-05 with `unit_name` `percent`

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

### Requirement: Price indicators
`price_indicator_daily` SHALL have one row per `listing_id` and `price_date` of `price_daily`, with
`trading_symbol_code`, `price_close_adjusted`, `close_adjusted_two_hundred_day_average_amount` (the
average adjusted close of the listing's last 200 price rows up to that date, empty when fewer than
200 exist), `close_adjusted_two_hundred_day_average_slope_ratio` (that average divided by the same
average 20 price rows earlier, minus 1; empty when either is empty), `close_adjusted_day_count` (rows
in the window, at most 200), `price_high_fifty_two_week_amount` and `price_low_fifty_two_week_amount` (the
highest `price_high` and lowest `price_low` of the listing over the price dates in the 364 days up to and
including that date), `currency_code` and `ingested_timestamp`.

It SHALL also have the strategy 004 indicators, over the listing's price rows up to and including that date:
`close_adjusted_sixty_day_change_ratio` (the adjusted close divided by the adjusted close 60 rows earlier, minus 1;
empty with fewer than 61 rows), `price_range_amount` (high minus low) and `price_range_ratio` (that divided by the
close), `true_range_amount` (the higher of the high and the previous close minus the lower of the low and the previous
close; high minus low on the listing's first row) and `true_range_ratio` (that divided by the close),
`price_range_sixty_day_average_amount`, `price_range_sixty_day_average_ratio`, `true_range_sixty_day_average_amount`
and `true_range_sixty_day_average_ratio` (simple averages of the last 60 rows; empty with fewer than 60 rows),
`efficiency_range_ratio` (`close_adjusted_sixty_day_change_ratio` divided by `price_range_sixty_day_average_ratio`),
`efficiency_true_range_ratio` (`close_adjusted_sixty_day_change_ratio` divided by
`true_range_sixty_day_average_ratio`) and `volume_sixty_day_average_count` (the simple average volume of the last 60
rows). The ranges SHALL use the reported high, low and close; the change SHALL use the adjusted close. Every column
SHALL carry a Unity Catalog description.

#### Scenario: Enough history
- **WHEN** `^GSPC` has more than 220 price rows up to a date
- **THEN** its row on that date has a 200-day average and a slope

#### Scenario: Too little history
- **WHEN** a listing has 150 price rows up to a date
- **THEN** its row on that date has `close_adjusted_day_count` 150 and an empty average and slope

#### Scenario: 52-week range
- **WHEN** EQT's highest high in the 364 days to 2026-11-03 is 68.24 and its lowest low 47.94
- **THEN** its row on 2026-11-03 has `price_high_fifty_two_week_amount` 68.24 and `price_low_fifty_two_week_amount` 47.94

#### Scenario: An efficient rise
- **WHEN** a listing's adjusted close rose 30% over its last 60 rows and its high minus low averaged 2% of the close
  over the last 60 rows
- **THEN** its row has `close_adjusted_sixty_day_change_ratio` 0.30, `price_range_sixty_day_average_ratio` 0.02 and
  `efficiency_range_ratio` 15

#### Scenario: A gap counts in the true range
- **WHEN** a listing closed at 100, then opened higher and traded between 104 and 106, closing at 105
- **THEN** that day's `price_range_amount` is 2 and `true_range_amount` is 6

#### Scenario: Too little history for the 60-day indicators
- **WHEN** a listing has 40 price rows up to a date
- **THEN** its row has the day's ranges but an empty change, empty averages and empty efficiency ratios
