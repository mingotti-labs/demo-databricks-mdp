# silver-domain-investments Specification

## Purpose
The first Silver Domain: conformed, typed tables in `silver_domain_investments`
that join the dividend portfolio story's sources (Wikipedia, SEC, Yahoo, RBA,
FRED, portfolio), with the SEC concept mapping applied, for gold to read.

## Requirements

### Requirement: Domain schema and sources
The tables SHALL live in schema `silver_domain_investments` of each target's
catalog and SHALL be built by one pipeline, `silver_domain_investments`
(display name `silver--domain--investments--<target>`), that reads only
`silver_landing` tables. Values SHALL be typed (dates as DATE, amounts and
rates as DECIMAL, counts as BIGINT). Every money amount SHALL have a
`currency_code` column. Each table SHALL carry `ingested_timestamp`: the
Landing row's, or the earliest of its input rows when a row combines several.
A column name SHALL say what the value is, ending in `_id`, `_key`, `_code`,
`_name`, `_url`, `_date`, `_timestamp`, `_amount`, `_count`, `_ratio` (a quotient such as a
P/E or a slope) or `_value` (a measured level that is not money, such as CPI index points);
numbers in names are words (`ten_year`); a flag starts
with `is_` or `has_`. A figure whose meaning is clear from its name and table
(`net_income`, `capex`) MAY stay plain; a figure that could be an amount or a
count SHALL carry the suffix. Each entity SHALL be defined in its own file,
named after its table. Inputs from outside the pipeline SHALL be `silver_landing` tables; a
table MAY read another table of this pipeline.

#### Scenario: A domain table is read
- **WHEN** a user reads any table in `silver_domain_investments`
- **THEN** its dates are DATE, its amounts are DECIMAL with a `currency_code`
  beside them, and `ingested_timestamp` is set

#### Scenario: No source outside Landing
- **WHEN** the pipeline's inputs are listed
- **THEN** every input table is in schema `silver_landing`

### Requirement: Companies
`company` SHALL have one row per SEC central index key that is or was in the
S&P 500 list, keyed by `company_id`: the SHA-256 hash (64 hex characters) of
`identifier_source_system_code` and the registry's number joined by `:` (`sec` and the
10-digit central index key). The row SHALL also carry
`identifier_source_system_code`, `central_index_key`, `company_name`,
`gics_sector_name` and `gics_sub_industry_name`. `company_id`
SHALL be treated as opaque. `company` SHALL NOT carry index columns: a company
can be in many indexes. Share classes of one company (one central index key)
SHALL share one row.

#### Scenario: Two share classes
- **WHEN** `GOOGL` and `GOOG` are both in the current list with one central
  index key
- **THEN** `company` has one row for that key

#### Scenario: The id is stable
- **WHEN** the pipeline runs twice on the same Landing data
- **THEN** every company has the same `company_id` both times

### Requirement: Markets
`market` SHALL have one row per ISO 10383 operating market, keyed by
`market_code` (the ISO 10383 market identifier code), from the ISO market
identifier code Landing table (the `iso-mic` change), with `market_name`,
`legal_entity_name`, `country_code` (ISO 3166), `city_name`, `website_url` and
`status_name`. Market segments SHALL NOT be rows.

#### Scenario: A known market
- **WHEN** the ISO list holds operating market `XASX`
- **THEN** `market` has one row for `XASX` with country code `AU`

### Requirement: Listings
`listing` SHALL have one row per `listing_id`: the SHA-256 hash of
`market_code` and `trading_symbol_code` joined by `:`. A listing is
one trading symbol on one market. It SHALL carry `market_code`,
`trading_symbol_code` (the Wikipedia form with dots, as in Landing),
`currency_code`, `company_id` (empty for an index benchmark) and the options
columns below. Listings SHALL
come from every symbol in the Wikipedia S&P 500 history and from the
`portfolio` benchmarks. The market of a symbol SHALL be the operating market identifier code
mapped from the `exchange_code` of the latest version of the symbol's Yahoo
calendar row (`NMS`, `NGM`, `NCM` to `XNAS`; `NYQ`, `PCX`, `ASE` to `XNYS`;
`BTS` and `CXI` to `XCBO`; `CMX` and `NYM` to `XNYM`; `FGI` and `SNP`, index
providers, to `XXXX`, ISO 10383's "no market"). `company_id` SHALL come from the
central index key of the symbol's latest Wikipedia version.

#### Scenario: A member resolves to a company
- **WHEN** `KO` is in the current list
- **THEN** `listing` has one row for `KO` whose `company_id` is the
  `company_id` of its central index key

#### Scenario: A member's market
- **WHEN** the latest Yahoo calendar row for `KO` has `exchange_code` `NYQ`
- **THEN** the `KO` listing has `market_code` `XNYS`

#### Scenario: A benchmark has no company
- **WHEN** a `portfolio` benchmark symbol is a market index
- **THEN** its `listing` row has an empty `company_id`

#### Scenario: A futures contract's market
- **WHEN** the latest Yahoo calendar row for `GC=F` has `exchange_code` `CMX`
- **THEN** the `GC=F` listing has `market_code` `XNYM`

#### Scenario: An index is not traded on a market
- **WHEN** the latest Yahoo calendar row for `^TRCCRB` has `exchange_code` `FGI`
- **THEN** the `^TRCCRB` listing has `market_code` `XXXX`, a row of `market`

### Requirement: Index membership history
`index_membership` SHALL have one row per listing per membership version, with
`index_code` (`SP500`), `listing_id`, `trading_symbol_code`, `date_added`, the
membership's `valid_from_timestamp` and `valid_to_timestamp` and `is_current`.
A current version SHALL have `valid_to_timestamp` 9999-12-31 (Landing's empty
value is replaced).

#### Scenario: A symbol leaves the index
- **WHEN** a weekly list no longer contains a symbol
- **THEN** its version has a real `valid_to_timestamp` and `is_current` false

#### Scenario: A current member
- **WHEN** a symbol is in the current list
- **THEN** its version has `valid_to_timestamp` 9999-12-31 and `is_current` true

### Requirement: Daily prices
`price_daily` SHALL have one row per listing and trading date fetched from Yahoo
(index members and benchmarks), with `listing_id`, `trading_symbol_code`,
`price_date`, `price_open`, `price_high`, `price_low`, `price_close` (as Yahoo
reports it), `price_close_adjusted`, `price_volume_count` and `currency_code`.

#### Scenario: A member's latest price
- **WHEN** `run_yahoo` has fetched a trading day for `KO`
- **THEN** `price_daily` has one row for the `KO` listing on that date with a
  DECIMAL `price_close` and `currency_code` `USD`

### Requirement: Dividends
`dividend` SHALL have one row per listing and ex-date, with `dividend_amount` as Yahoo
reports it, `currency_code`, `dividend_amount_in_australian_dollars` converted at the RBA
AUD/USD rate of the latest RBA date on or before the ex-date (empty when no such
rate is held), the pay date with `pay_date_is_estimated`, and `is_special`. The
pay date SHALL be the Yahoo calendar's pay date when a calendar version has the
same ex-date, otherwise the ex-date plus the `pay_date_offset_days` setting. A
dividend SHALL be special when its amount is more than twice the median of the
same listing's previous four dividends.

#### Scenario: A known pay date
- **WHEN** a Yahoo calendar version for `KO` has ex-date 2026-09-15 and pay
  date 2026-10-01
- **THEN** the `KO` dividend with ex-date 2026-09-15 has pay date 2026-10-01
  and `pay_date_is_estimated` false

#### Scenario: An estimated pay date
- **WHEN** no calendar version matches a dividend's ex-date and the setting is
  14
- **THEN** its pay date is the ex-date plus 14 days and
  `pay_date_is_estimated` is true

#### Scenario: A one-off amount
- **WHEN** a listing's previous four dividends were 0.50 each and the next is
  2.00
- **THEN** that dividend has `is_special` true

### Requirement: Company fundamentals per filing
`company_fundamentals` SHALL have one row per `company_id` and `valid_from_date`,
the filing date of one of its 10-K, 10-K/A, 10-Q or 10-Q/A filings (that pair
is the business key), with `valid_to_date` the day before the company's next
`valid_from_date`, or 9999-12-31 for its latest filing. Each row SHALL carry
`form_code`, `accession_number`, the period end the filing reports, one column
per figure in the `portfolio` concept mapping (`earnings_per_share_amount`,
`shares_outstanding_count` and `depreciation_and_amortisation_amount` carry a
suffix; the others are plain), free cash flow (operating cash
flow minus capital expenditure), total debt (long-term plus short-term),
`earnings_before_interest_tax_depreciation_amortisation` (operating income
plus depreciation and amortisation) and a map of the concept
used for each figure. Values SHALL come only from facts known at the filing
date, in USD (and `shares` or `USD/shares` for share counts and earnings per share). Balance
sheet figures and the share count SHALL be those the filing reports for its
period end. `weighted_average_shares_basic_count` SHALL be the filing's weighted
average basic share count (all share classes) for the shortest period ending at
its period end (the quarter on a 10-Q, the year on a 10-K), never a sum of periods;
`shares_outstanding_count` stays the cover-page count. Each row SHALL also carry the
last 10 annual earnings known at its filing date: of the company's 10-K and 10-K/A
filings on or before `valid_from_date`, the latest per period end, the last 10 by
period end with a `net_income`. `earnings_year_count` SHALL be how many (at most 10),
`earnings_ten_year_average_amount` their plain average, `consumer_price_index_value`
the US CPI (all items, not seasonally adjusted) of the latest month with a value on
or before the row's period end, and `earnings_ten_year_average_inflation_adjusted_amount`
the average of each year's `net_income` x (this row's CPI / that year's CPI, by the
same month rule). These four columns SHALL be empty when no annual earnings are known
and SHALL carry a Unity Catalog description. Income and cash flow figures SHALL be the trailing twelve months to
the period end: a 10-K's annual value, or for a 10-Q the latest annual value
plus this year's year-to-date minus the prior year's year-to-date, empty when a
part is missing. For each figure it SHALL take the highest-priority concept that
has a value. When `Liabilities` has no value, `total_liabilities` SHALL be
`liabilities_and_equity` minus `total_equity`. A successor central index key in
the predecessor list SHALL take the predecessor's filings dated before its own
first filing.

#### Scenario: Priority between concepts
- **WHEN** a company reports both `NetIncomeLoss` and `ProfitLoss` for a year
- **THEN** `net_income` is the `NetIncomeLoss` value and the concept map says
  `NetIncomeLoss`

#### Scenario: Validity between filings
- **WHEN** a company filed a 10-Q on 2026-05-01 and its next 10-Q on 2026-08-01
- **THEN** the row with `valid_from_date` 2026-05-01 has `valid_to_date`
  2026-07-31, and the row from 2026-08-01, its latest, has `valid_to_date`
  9999-12-31

#### Scenario: Trailing twelve months from a 10-Q
- **WHEN** a company's last annual net income is 100, its year-to-date net
  income in a 10-Q is 30 and the prior year's same year-to-date is 20
- **THEN** that row's `net_income` is 110

#### Scenario: A restatement is a new row
- **WHEN** a 10-K/A restates a 10-K's values
- **THEN** the 10-K's row keeps its values until the day before the 10-K/A's
  filing date, and the 10-K/A's row has the restated values

#### Scenario: Liabilities not reported
- **WHEN** a company reports `LiabilitiesAndStockholdersEquity` of 100 and
  total equity of 40 but no `Liabilities`
- **THEN** `total_liabilities` is 60 and the concept map says it was derived

#### Scenario: A predecessor's history
- **WHEN** the predecessor list maps `0002115436` to `0000034088`
- **THEN** the company with central index key `0002115436` has the filings made under
  `0000034088` before its own first filing

#### Scenario: A company with several share classes
- **WHEN** a 10-Q has no cover-page share count and reports weighted average basic
  shares of 880 million for the quarter and 885 million for the year to date
- **THEN** its row has an empty `shares_outstanding_count` and
  `weighted_average_shares_basic_count` 880000000

#### Scenario: Ten-year average at a 10-K
- **WHEN** a company's latest 10-K filed by a row's filing date ends in September 2025, CPI
  of September 2025 is 324.8, and its last two of ten annual earnings are 93.74 bn (CPI 315.301)
  and 112.01 bn (CPI 324.8)
- **THEN** `earnings_year_count` is 10, `consumer_price_index_value` is 324.8, those two years
  count as 96.56 bn and 112.01 bn in the inflation-adjusted average, and as 93.74 bn and
  112.01 bn in the plain average

#### Scenario: Fewer than ten years
- **WHEN** a company has filed only four 10-Ks by a row's filing date
- **THEN** `earnings_year_count` is 4 and both averages are over those four years

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

### Requirement: Options on the listing
`listing` SHALL carry, as of the latest Yahoo fetch, `has_options`,
`option_expiry_count`, `option_nearest_monthly_expiry_date`,
`option_open_interest` and `option_volume`. There SHALL be no separate options
table. A listing Yahoo has no options row for SHALL have these columns empty.

#### Scenario: A listing without options
- **WHEN** Yahoo lists no options for a symbol
- **THEN** its listing has `has_options` false

### Requirement: Run job and verification
Job `run_investments` SHALL run the pipeline, then the gold pipeline
`gold_analytics_gateway` (after the silver verification when it runs, and not after
a failed one), and, when its `verify` parameter
is `true`, a verification that fails when: a table's key is not unique; a
current index member has no `listing` row or its listing has no `company`; a
symbol in Landing's Yahoo prices, events or options has no `listing`; one
symbol maps to more than one central index key across Wikipedia versions; a
listing has no market or its market is not in `market`; a current member has no price in the last 7
days; a company's `company_fundamentals` validity ranges overlap or leave a gap,
or it has other than one row ending 9999-12-31; fewer than 95% of companies with
a current index membership have `net_income` on their current row; a dividend
since the first held AUD/USD date has no `dividend_amount_in_australian_dollars`; or a
rate's latest date is more than 7 days old.

#### Scenario: Verification passes in dev
- **WHEN** `run_investments` runs in dev with `verify=true` after every source
  has run
- **THEN** every check passes and the run succeeds

#### Scenario: A missing company
- **WHEN** a current member's listing has no `company` row
- **THEN** the verification fails and names the symbol

#### Scenario: Gold after silver
- **WHEN** `run_investments` runs, with `verify` true or false
- **THEN** the gold pipeline starts only after the silver pipeline (and the silver
  verification, when it runs) has succeeded

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
