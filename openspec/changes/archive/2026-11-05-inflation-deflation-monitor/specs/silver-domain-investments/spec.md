## ADDED Requirements

### Requirement: Market rate indicators
`market_rate_indicator_daily` SHALL have one row per `rate_code` and `indicator_date` for every `^GSPC` price
date, for `us_cpi_all_items_not_seasonally_adjusted` (the CPI index), `us_federal_funds_effective_rate`,
`us_cpi_change_previous_reading_percent`,
`us_cpi_change_twelve_months_percent` and `us_real_federal_funds_rate`, with `rate_name`, `rate_value` (the
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

## MODIFIED Requirements

### Requirement: Price indicators
`price_indicator_daily` SHALL have one row per `listing_id` and `price_date` of `price_daily`, with
`trading_symbol_code`, `price_close_adjusted`, `close_adjusted_two_hundred_day_average_amount` (the
average adjusted close of the listing's last 200 price rows up to that date, empty when fewer than
200 exist), `close_adjusted_two_hundred_day_average_slope_ratio` (that average divided by the same
average 20 price rows earlier, minus 1; empty when either is empty), `close_adjusted_day_count` (rows
in the window, at most 200), `price_high_fifty_two_week_amount` and `price_low_fifty_two_week_amount` (the
highest `price_high` and lowest `price_low` of the listing over the price dates in the 364 days up to and
including that date), `currency_code` and `ingested_timestamp`. Every column SHALL carry a
Unity Catalog description.

#### Scenario: Enough history
- **WHEN** `^GSPC` has more than 220 price rows up to a date
- **THEN** its row on that date has a 200-day average and a slope

#### Scenario: Too little history
- **WHEN** a listing has 150 price rows up to a date
- **THEN** its row on that date has `close_adjusted_day_count` 150 and an empty average and slope

#### Scenario: 52-week range
- **WHEN** EQT's highest high in the 364 days to 2026-11-03 is 68.24 and its lowest low 47.94
- **THEN** its row on 2026-11-03 has `price_high_fifty_two_week_amount` 68.24 and `price_low_fifty_two_week_amount` 47.94
