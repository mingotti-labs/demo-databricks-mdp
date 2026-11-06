## Context

- SEC: `src/common/fetch_sec.py` keeps only the concepts in `bronze_portfolio_publish.concept_mapping_scd2` and writes a
  company's facts file when its content hash changes. Silver `company_fundamentals`
  (`src/layers/silver/domain/investments/company_fundamentals.py`) picks, per filing (`cik`, `accn`, figure), the
  highest-priority mapped concept with a value; `duration` figures become trailing twelve months. Figures are declared
  in `FIGURES` in `src/common/investments.py`, with descriptions in `COMPANY_FUNDAMENTALS_COMMENTS`.
- Gold `valuation_daily_index_member` joins each member's valid filing row (`filing_valid_from_date`) and computes
  `market_value_amount` from price and share count.
- Yahoo: a new benchmark in `data/portfolio/benchmarks.csv` loads its full history (`plan()` in
  `src/common/yahoo_market.py`).

## Goals / Non-Goals

**Goals:** a revenue figure per filing; price-to-sales per member and day; the five bear funds' prices.

**Non-Goals:** the strategy rules and table, the dashboard, revenue before the members' price history (gold starts
2025-10-28), non-US filers.

## Decisions

### D1. Revenue concepts and priority (probe P2)

P2 (`references/poc/strategies/p2_result.txt`, SEC companyfacts, 2026-11-06): Apple reports
`RevenueFromContractWithCustomerExcludingAssessedTax` since 2018 (`SalesRevenueNet` and `Revenues` before), NVIDIA and
Realty Income `Revenues`, Palantir only the contract concept, JPMorgan `RevenuesNetOfInterestExpense` on its latest
filings, Berkshire both `Revenues` and the contract concept. Priority: `Revenues` (total, includes non-contract revenue
such as interest and rent), then the contract concept, then `RevenuesNetOfInterestExpense`, `SalesRevenueNet`,
`RevenueFromContractWithCustomerIncludingAssessedTax`. Silver already resolves the priority per filing, so a company that
switched concept is handled. Rejected: one concept per company (wrong for switchers), summing concepts (double counts).

### D2. Price-to-sales in the member table

`price_to_sales_ratio = market_value_amount / revenue_trailing_twelve_months_amount`, empty when either is missing or
revenue is not above zero. It sits next to the P/E inputs in `valuation_daily_index_member` (no new table, same day and
member grain). The index P/E and `is_used` do not change: a missing revenue does not exclude a member.

### D3. Bear funds as benchmarks

Five rows of kind `bear_fund` (probe P0, `references/poc/strategies/p0_result.txt`): SQQQ (NGM, from 2010), PSQ, SH, SDS
(PCX, 2006), SPXU (PCX, 2009). Both exchange codes already map (`XNAS`, `XNYS`). Benchmarks are listings, not index
members, so they get prices and indicators only.

### D4. Rollout

The concept mapping change makes `run_sec` write every company's facts file once (about 20 minutes in prd). CI runs
`investments` before `portfolio`, `sec` and `yahoo`, so prd needs one more `run--investments--prd` afterwards (the user
starts it; the classifier blocks Claude in prd).

## Risks / Trade-offs

- [A filing reports none of the five concepts] → `revenue` empty, `price_to_sales_ratio` empty; the dev verification
  reports the share of members without it (P2 suggests few).
- [`Revenues` of a bank includes gross interest income] → a bank's price-to-sales looks low; banks are not the
  candidates this screen looks for (above 15).
- [The refetch takes long in prd] → once only; later runs write changed companies only.

## Migration Plan

Merge, let CI run, then one manual `run--investments--prd`; compare prd with dev (revenue coverage, a hand check of one
company's price-to-sales). Rollback: revert the PR; the extra facts rows are harmless.

## Open Questions

None.
