## Purpose

The first Silver Domain: conformed, typed tables in `silver_domain_investments`
that join the dividend portfolio story's sources (Wikipedia, SEC, Yahoo, RBA,
FRED, portfolio), with the SEC concept mapping applied, for gold to read.

## ADDED Requirements

### Requirement: Domain schema and sources
The tables SHALL live in schema `silver_domain_investments` of each target's
catalog and SHALL be built by one pipeline, `silver_domain_investments`
(display name `silver--domain--investments--<target>`), that reads only
`silver_landing` tables. Values SHALL be typed (dates as DATE, amounts and
rates as DECIMAL, counts as BIGINT). Every money amount SHALL have a
`currency_code` column. Each table SHALL carry `ingested_timestamp`: the
Landing row's, or the earliest of its input rows when a row combines several.

#### Scenario: A domain table is read
- **WHEN** a user reads any table in `silver_domain_investments`
- **THEN** its dates are DATE, its amounts are DECIMAL with a `currency_code`
  beside them, and `ingested_timestamp` is set

#### Scenario: No source outside Landing
- **WHEN** the pipeline's inputs are listed
- **THEN** every input table is in schema `silver_landing`

### Requirement: Companies
`company` SHALL have one row per SEC CIK that is or was in the S&P 500 list,
keyed by `company_key`, with `sec_central_index_key` (the CIK), the company
name, GICS sector and sub-industry, the earliest date added to the index, and
`in_index`, true when any of its symbols is in the current list. Share classes
of one company (one CIK) SHALL share one row.

#### Scenario: Two share classes
- **WHEN** `GOOGL` and `GOOG` are both in the current list with one CIK
- **THEN** `company` has one row for that CIK with `in_index` true

#### Scenario: A company left the index
- **WHEN** a CIK's only symbol has no current version in the list
- **THEN** its `company` row remains with `in_index` false

### Requirement: Index membership history
`index_membership` SHALL have one row per symbol per membership version, with
`index_code` (`SP500`), `symbol`, `company_key`, the date added, the
membership's valid-from and valid-to timestamps and `is_current`.

#### Scenario: A symbol leaves the index
- **WHEN** a weekly list no longer contains a symbol
- **THEN** its version has a valid-to timestamp and `is_current` false

### Requirement: Daily prices
`price_daily` SHALL have one row per symbol and trading date fetched from Yahoo
(index members and benchmarks), with the close as Yahoo reports it (not the
adjusted close), the volume and `currency_code`.

#### Scenario: A member's latest price
- **WHEN** `run_yahoo` has fetched a trading day for `KO`
- **THEN** `price_daily` has one row for `KO` on that date with a DECIMAL close
  and `currency_code` `USD`

### Requirement: Dividends
`dividend` SHALL have one row per symbol and ex-date, with the amount as Yahoo
reports it, `currency_code`, `amount_aud` converted at the RBA AUD/USD rate of
the latest RBA date on or before the ex-date (empty when no such rate is held),
the pay date with `pay_date_is_estimated`, and `is_special`. The pay date SHALL
be the Yahoo calendar's pay date when a calendar version has the same ex-date,
otherwise the ex-date plus the `pay_date_offset_days` setting. A dividend SHALL
be special when its amount is more than twice the median of the same symbol's
previous four dividends.

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
- **WHEN** a symbol's previous four dividends were 0.50 each and the next is
  2.00
- **THEN** that dividend has `is_special` true

### Requirement: Company fundamentals per filing
`company_fundamentals` SHALL have one row per company and `valid_from_date`,
the filing date of one of its 10-K, 10-K/A, 10-Q or 10-Q/A filings (that pair
is the business key), with `valid_to_date` the day before the company's next
`valid_from_date`, or 9999-12-31 for its latest filing. Each row SHALL carry
the form, the accession number, the period end the filing reports, one column
per figure in the `portfolio` concept mapping, free cash flow (operating cash
flow minus capital expenditure), total debt (long-term plus short-term), EBITDA
(operating income plus depreciation and amortisation) and a map of the concept
used for each figure. Values SHALL come only from facts known at the filing
date, in USD (and `shares` or `USD/shares` for share counts and EPS). Balance
sheet figures and the share count SHALL be those the filing reports for its
period end. Income and cash flow figures SHALL be the trailing twelve months to
the period end: a 10-K's annual value, or for a 10-Q the latest annual value
plus this year's year-to-date minus the prior year's year-to-date, empty when a
part is missing. For each figure it SHALL take the highest-priority concept that
has a value. When `Liabilities` has no value, `total_liabilities` SHALL be
`liabilities_and_equity` minus `total_equity`. A successor CIK in the
predecessor list SHALL take the predecessor's filings dated before its own
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
- **THEN** the company with CIK `0002115436` has the filings made under
  `0000034088` before its own first filing

### Requirement: Rates
`rate_daily` SHALL have one row per rate and date for AUD/USD (RBA `FXRUSD`),
the RBA cash rate target (`FIRMMCRTD`), the US 10-year Treasury yield (`DGS10`),
the effective federal funds rate (`DFF`) and the Fed target range limits
(`DFEDTARU`, `DFEDTARL`), with a `rate_code`, the value, its unit, the source
and the source's series id.

#### Scenario: The latest cash rate
- **WHEN** RBA's latest cash rate target is 4.60
- **THEN** `rate_daily` has that value under the cash rate's `rate_code` on its
  date

### Requirement: Options activity
`options_activity` SHALL have one row per symbol with whether options are
listed, the number of expiries, the nearest monthly expiry, its open interest
and volume, as of the latest Yahoo fetch.

#### Scenario: A symbol without options
- **WHEN** Yahoo lists no options for a symbol
- **THEN** its row has options listed false

### Requirement: Run job and verification
Job `run_investments` SHALL run the pipeline and, when its `verify` parameter
is `true`, a verification that fails when: a table's key is not unique; a
current index member has no `company` row; a current member has no price in
the last 7 days; a company's `company_fundamentals` validity ranges overlap or
leave a gap, or it has other than one row ending 9999-12-31; fewer than 95% of
companies in the index have `net_income` on their current row; a dividend since the first
held AUD/USD date has no `amount_aud`; or a rate's latest date is more than 7
days old.

#### Scenario: Verification passes in dev
- **WHEN** `run_investments` runs in dev with `verify=true` after every source
  has run
- **THEN** every check passes and the run succeeds

#### Scenario: A missing company
- **WHEN** a current member's CIK has no `company` row
- **THEN** the verification fails and names the symbol
