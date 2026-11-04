## MODIFIED Requirements

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
`shares_outstanding_count` stays the cover-page count. Income and cash flow figures SHALL be the trailing twelve months to
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
