## Context

See proposal.md. Landing tables today (2026-10-30, `databricks tables list`):

| Source | Tables | dev | prd |
|---|---|---|---|
| acnc | charity_register | yes | yes |
| airroi | market_metrics_all, market_summary | yes | no |
| clickstream | web_events | yes | no |
| geonames | country_info, admin1_codes, admin2_codes, cities | no (dropped 2026-10-29) | yes |
| iso | country_codes, subdivision_codes | yes | yes |
| neon | customers, products, orders, order_items | yes | no |
| nsw_spatial | property | yes | yes |
| portfolio | benchmarks, concept_mapping, predecessor_ciks, risk_levels, settings, target_mix | yes | yes |
| sec | company_facts, company_tickers | yes | yes |
| ungm | unspsc_public | yes | yes |
| wikipedia | sp500_constituents | yes | yes |
| yahoo | calendar, events, options, prices | yes | yes |

25 tables in dev, 22 in prd. Every one is a streaming table filled by
`create_auto_cdc_flow` from a temporary view over the Bronze Publish table's
change feed (`land_changes`), built by the source's silver pipeline
(`silver--<source>--<target>`; acnc's is `silver_normalised_acnc`).

## Goals / Non-Goals

**Goals:**
- Every Landing table in `silver_landing`, named `<source>__<entity>`, in dev
  and prd, with the same rows as before.
- Nothing left that reads or writes a `silver_landing_<source>` schema, so iac
  can drop them.

**Non-Goals:**
- The standard edition (`cicd/databricks/standard.yml`) and iac's
  `single_workspace`: they keep one schema per source (user's decision).
- Other schema families (`bronze_<source>_publish`,
  `silver_normalised_<source>`).
- Fixing the missing natural-key comments on Landing columns (its own change,
  noted 2026-10-28).

## Decisions

**D1. Rebuild, don't move.** A Landing table is cheap to rebuild: a new
streaming table reads the whole change feed of its Bronze Publish table, and
`land_changes` gives the same rows (`correct-platform-timestamps` P4: Landing
equals a full read). Renaming a pipeline's streaming table into another schema
is not a documented operation, and a move would keep the flow's checkpoint
tied to the old name. The only value that differs after a rebuild is
`transformed_timestamp` (rebuild time), which fits the rule that a step stamps
the rows it inserts.

**D2. Name: `<source>__<entity>`** (double underscore), entity = today's table
name, so `silver_landing_acnc.charity_register` becomes
`silver_landing.acnc__charity_register`. Source names already contain single
underscores (`nsw_spatial`), so the double underscore keeps the split
unambiguous. The `mdp_source_system` tag is unchanged.

**D3. Pipelines keep their keys and display names**; only the default
`schema:` changes, to `silver_landing`. A key change would make DAB delete and
recreate the pipeline (NAMING.md "Bundle resources"). Whether a deployed
pipeline accepts a new default schema is probe P1. If it does not, the
pipelines keep their old default schema until a follow-up recreates them, and
the iac follow-up must wait for that; every table name is qualified, so the
default schema is not used for writing.

**D4. Old tables are dropped by hand, after the new ones verify.** Removing a
dataset from the code leaves its table in place
(`correct-platform-timestamps` P1). Each old table and its hidden
`__materialization_mat_*` twin is dropped with the user's approval, per
environment, after `verify_silver_landing` passes on the new tables. Old and
new coexist only between the run and the drop (up to +94 table slots on
388/500).

**D5. The tag step filters by prefix.** `design_patterns.yml` gives each source
`silver_landing: silver_landing_change_feed_python`; `tag_design_patterns.py`
lists the schema's tables and, for `silver_landing`, tags only names starting
with `<source>__`, so a source never tags another source's tables.

**D6. The spec checker keeps sources apart by prefix.** A Silver Normalised
spec may read only `silver_landing.<source>__*`; `normalised_spec.py` checks
the prefix instead of the schema name. Base entities keep the Landing entity
name without the prefix (`charity_register`), as the silver-normalised spec
already requires ("keeps its Silver Landing table's name").

**D7. Silver Normalised keeps its timestamps.** acnc and airroi rebuild
Normalised from Landing and keep `transformed_timestamp` on unchanged rows by
comparing with the previous Normalised table (`correct-platform-timestamps`
P3). A changed Landing `transformed_timestamp` must not count as a change;
checked in dev by counting rows restamped by the first run after the
rebuild (expected 0).

**D8. One PR, run per source in dev, then prd through CI.** In dev, each
source's silver pipeline is run as the service principal
(`cicd/run_dev.py <unit>`); airroi's run job fetches from the paid API, so
for airroi only the silver pipeline is started (`databricks pipelines
start-update`), not `run_airroi`. In prd, merging runs every auto-run unit; each
unit's silver pipeline creates its new Landing tables in that run.

## Probes

| Probe | Question | How |
|---|---|---|
| P1 | Does a deployed pipeline accept a new default `schema:` and keep working? | A scratch pipeline in dev (`pattern_bronze`), one dataset, run; change its schema to `pattern_bronze_publish` with `databricks pipelines update`, run again. Scripts and results in `references/poc/single-silver-landing-schema/`. |

The rebuild itself (row parity with bronze) is checked by
`verify_silver_landing`, not a separate probe.

## Risks / Trade-offs

- [P1 fails] -> D3's fallback: keep the old default schema, all writes are
  qualified; the iac drop waits for a follow-up that recreates the pipelines.
- [A rebuilt table differs from the old one] -> `verify_silver_landing` checks
  parity with bronze per table before any drop; the old table is still there
  to compare.
- [Normalised restamps every row] -> D7's check catches it in dev, before
  prd.
- [prd run time] -> about 45 minutes through the prd gate; no source re-fetch
  is needed for Landing, but CI runs whole units.
- [Standard edition no longer matches the code] -> accepted (user).

## Migration Plan

1. Probe P1.
2. Code, specs and docs; draft PR; `deploy-dev` deploys as the service
   principal.
3. dev, one source at a time: run its unit (airroi: silver pipeline only),
   `verify_silver_landing` passes, D7 check for acnc and airroi.
4. User approves; drop the 25 old dev tables and their twins.
5. Merge: CI runs the units in prd; check the 22 new prd tables (row counts
   against the old ones).
6. User approves; drop the 22 old prd tables and their twins.
7. Tell iac the twelve schemas are empty (follow-up change there).

Rollback before step 4/6: revert the PR; the old tables are untouched until
dropped.
