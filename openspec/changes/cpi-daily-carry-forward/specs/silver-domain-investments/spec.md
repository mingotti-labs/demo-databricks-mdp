## MODIFIED Requirements

### Requirement: Market rates
`market_rate_daily` SHALL have one row per rate and date for the Australian
dollar in US dollars (RBA `FXRUSD`), the RBA cash rate target (`FIRMMCRTD`), the
US 10-year Treasury yield (`DGS10`), the effective federal funds rate (`DFF`)
and the Fed target range limits (`DFEDTARU`, `DFEDTARL`), with a `rate_code`
(`australian_dollar_in_us_dollars`, `rba_cash_rate_target`,
`us_10_year_treasury_yield`, `us_federal_funds_effective_rate`,
`us_federal_funds_target_upper`, `us_federal_funds_target_lower`), `rate_name`,
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
