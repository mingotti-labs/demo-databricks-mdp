## Context

`company_fundamentals` picks each figure by kind: `instant` (balance sheet at the period end),
`duration` (trailing 12 months), `cover` (cover-page share count). Probes (2026-11-04,
`references/poc/market-climate/`): P2 counted 42 current members without a cover count on their
latest filing, 24 of them with one on an older filing (some 10+ years old); P3 showed SEC sent no
share facts at all for the latest filings of MA, NKE, UPS, FOXA, HSY, and that HSY's
`CommonStockSharesOutstanding` covers one class only; P4 showed weighted average basic shares current
for MA, NKE, UPS, FOXA, GOOGL, AAPL, but not HSY (stopped 2015).

## Goals / Non-Goals

**Goals:** a share count for (nearly) every member's latest filing; no change to existing columns.

**Non-Goals:** choosing between the two counts (gold does that); carrying old cover counts forward
(stale); per-class counts (not in company facts).

## Decisions

### D1. A new kind, `period`
A weighted average share count is a duration fact, but summing quarters (the `duration` kind) would
be wrong. `period` takes the fact whose end is the filing's period end with the shortest duration:
the quarter on a 10-Q (not the year-to-date), the year on a 10-K. Same known-at-filing rule as the
others (facts of that accession).

### D2. Keep both counts
`shares_outstanding_count` (cover, a point in time near the filing date) stays as it is; the new
column is an average over the period. Gold uses the cover count when present, else the weighted
average (story design). Rejected: replacing the cover count (it is more current where it exists).

### D3. Refetch by content change
`fetch_sec.py` writes a company's file when its mapped facts change (content hash). The new concept
changes every company's facts, so one `run_sec` refetches all; no `reload` parameter is needed.

## Risks / Trade-offs

- [A handful of companies report neither figure, e.g. HSY] -> counted in gold
  (`members_without_shares_count`), not hidden; the verification bounds how many.
- [One `run_sec` writes about 500 files] -> the same as a normal week after many filings; append-only.

## Migration Plan

Merge -> CI deploys and runs `investments`, `portfolio` -> run `run_sec`, then `run_investments` by
hand (prd and dev). Rollback: revert; the extra raw rows are harmless.

## Open Questions

None.
