## Context

See proposal.md - Why. Both `phase3b-neon-scd-modeling` and
`phase3c-ungm-unspsc-ingestion` built their snapshot-based Auto CDC flows
by following the Databricks docs' own example pattern literally — which
happens to wrap the source in an intermediate `@dp.materialized_view()`
snapshot — without independently testing whether that wrapper was actually
required. A direct question about it led to testing the simpler
alternative for real.

## Goals / Non-Goals

**Goals:**
- Confirm (not assume) whether `create_auto_cdc_from_snapshot_flow`
  requires its source to be a pipeline-internal dataset
- If not required, remove the wrapper entirely — simpler than deciding
  where an implementation-detail object should live or whether to mark it
  `private=True`
- Leave all affected SCD data in a genuinely correct state, not just a
  row-count-matching one

**Non-Goals:**
- Re-litigating any other part of the Neon or UNGM SCD design — this
  change is scoped to the snapshot-removal and its cleanup only

## Decisions

**Tested the direct-`_raw` approach on one table first (`customers_scd1`),
not all six at once.**
Minimized blast radius for an experiment with a genuinely uncertain
outcome. It worked cleanly on the first attempt (200 rows, `id=1`'s
previously-tracked update correctly reflected) — only then was it
propagated to the remaining 5 flows (4 Neon + 1 UNGM) and the 5 snapshot
files deleted.

**Discovered mid-migration: switching `source` on an already-run flow
pollutes SCD2 history for Streaming-Table-backed sources.**
After propagating the change and re-running, row counts alone looked
plausible (`customers_scd2` showed 401, not obviously wrong without doing
the arithmetic) but a direct check — grouping by all tracked columns and
counting duplicates — found 199 of Neon's 200 customers had two "versions"
with byte-identical field values: a false history entry, not a real
tracked change. `products_scd2` had the same pattern. UNGM's
`unspsc_public_scd2` — sourced from a Materialized View, not a Streaming
Table — was unaffected (0 duplicates), the only structural difference
between the two being what kind of table `source` was pointed at before
vs. after the switch. Not fully explained (the exact internal mechanism
Auto CDC uses to detect this "change" is undocumented at the level of
detail needed to be certain), but the empirical pattern is clear and
reproducible: don't switch a snapshot flow's `source` identity on an
already-run flow without expecting to need a full refresh afterward.

**Fixed with a full refresh of the whole Neon SCD pipeline, not a
selective per-table refresh.**
The CLI's `--full-refresh` flag resets every table in the pipeline; a
selective refresh exists via the REST API's `full_refresh_selection`
field, but confirming its exact syntax risked another failed attempt for a
marginal benefit — the unaffected SCD1 tables are cheap to rebuild
(deterministic, "latest value per key" either way) and rebuilding them
alongside the genuinely-broken SCD2 tables cost nothing but a little
redundant compute. UNGM's pipeline was not touched at all, since it was
already confirmed clean.

**Re-proved SCD2 history-tracking with a fresh customer (`id=3`), not by
re-checking `id=1`/`id=2`.**
The full refresh discarded the two previously-demonstrated version
histories (`id=1`, `id=2` — both now show only their current state, no
memory of the pre-update value). Using a fresh, never-before-touched
customer for the retrofit-test avoided any ambiguity about whether a
result reflected old, partially-refreshed state versus a genuinely fresh
history record.

## Risks / Trade-offs

- [The full refresh destroyed the originally-proven `id=1`/`id=2` SCD2
  history] → Accepted and disclosed directly — the original proof remains
  fully documented in `phase3b-neon-scd-modeling`'s archived tasks.md; a
  fresh, equally rigorous proof (`id=3`) was captured before closing this
  out.
- [The exact cause of the source-switch duplication isn't fully understood
  at the mechanism level] → Documented as an empirical finding with a clear
  reproduction pattern (Streaming Table source + source-identity switch on
  an already-run flow) rather than a guessed root cause — sufficient to
  avoid repeating the mistake, even without a complete internal explanation.

## Migration Plan

Already applied directly (dev): all 6 Neon/UNGM SCD flows repointed at
their raw tables, 5 snapshot files removed, Neon SCD pipeline full-refreshed
and re-verified clean, UNGM pipeline confirmed already clean and left
untouched, 2 display names renamed. Promotion to `tst`/`prd` happens via
CI/CD on merge, per this project's established convention. Rollback:
revert the source-file changes; the removed snapshot views can be
recreated from git history if ever needed.
