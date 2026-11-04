## MODIFIED Requirements

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
