## Why

The market climate story (planning `docs/superpowers/specs/2026-11-04-market-climate-story-design.md`,
change 1 of 4) needs each S&P 500 member's market value: price times shares. Probe P2
(`references/poc/market-climate/`) found 42 of 503 current members with no
`shares_outstanding_count` on their latest filing. P3 and P4 found why: a company with several
share classes (MA, NKE, UPS, FOX, NWS and others) reports its cover-page share count per class, and
SEC's company facts leave out per-class values, so no total arrives (MA since 2010, NKE since 2015).
SEC's weighted average basic shares (`us-gaap:WeightedAverageNumberOfSharesOutstandingBasic`) does
cover all classes and is current for those companies (P4: MA 883 m, NKE 1.48 bn, UPS 850 m, FOXA 421 m).

## What Changes

- `data/portfolio/concept_mapping.csv`: new figure `weighted_average_shares_basic_count` mapped to
  `us-gaap:WeightedAverageNumberOfSharesOutstandingBasic`.
- `src/common/investments.py`: the figure, with a new kind `period`: the filing's own value for the
  shortest period ending at its period end (the quarter on a 10-Q, the year on a 10-K), never a
  trailing 12-month sum.
- `company_fundamentals`: new column `weighted_average_shares_basic_count`. Existing columns
  unchanged; `shares_outstanding_count` stays the cover-page count.
- SEC fetch: no code change. The fetch keeps only mapped concepts, so the new concept changes every
  company's facts file and the next `run_sec` writes all of them again (append-only raw).
- Verification: a check that members with neither share figure stay few, and that MA's latest row
  has a weighted average count.
- Not in this change: using the count for market value (gold, change 3 `market-climate-gold`: cover
  count, else weighted average).

## Capabilities

### Modified Capabilities
- `silver-domain-investments`: `company_fundamentals` carries the weighted average basic share count.

## Impact

- No new table. More rows in the SEC raw and Landing tables (one concept more per filing).
- Run order after merge: CI runs the affected units alphabetically (`investments`, `portfolio`), but
  the fetch needs `portfolio` (mapping) first, then `sec`, then `investments`. After the prd run,
  run `run_sec` and then `run_investments` by hand; in dev the same order with `cicd/run_dev.py`.

## Model

Sonnet: a new figure in an existing mapping and one new pick in the existing view.
