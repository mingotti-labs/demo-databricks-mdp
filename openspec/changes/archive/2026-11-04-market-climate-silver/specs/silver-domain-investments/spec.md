## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Price indicators
`price_indicator_daily` SHALL have one row per `listing_id` and `price_date` of `price_daily`, with
`trading_symbol_code`, `price_close_adjusted`, `close_adjusted_two_hundred_day_average_amount` (the
average adjusted close of the listing's last 200 price rows up to that date, empty when fewer than
200 exist), `close_adjusted_two_hundred_day_average_slope_ratio` (that average divided by the same
average 20 price rows earlier, minus 1; empty when either is empty), `close_adjusted_day_count` (rows
in the window, at most 200), `currency_code` and `ingested_timestamp`. Every column SHALL carry a
Unity Catalog description.

#### Scenario: Enough history
- **WHEN** `^GSPC` has more than 220 price rows up to a date
- **THEN** its row on that date has a 200-day average and a slope

#### Scenario: Too little history
- **WHEN** a listing has 150 price rows up to a date
- **THEN** its row on that date has `close_adjusted_day_count` 150 and an empty average and slope
