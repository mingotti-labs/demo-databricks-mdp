## Why

The Free Edition metastore allows 500 tables and holds 456 (2026-11-01). The
Silver Domain `silver_domain_investments` adds 36 slots (9 views, dev and prd),
which takes the count to 492 and past the 488 stop line, and gold needs more.
The user asked (2026-11-01) for a clean-up before that merges. The first
candidate is Neon: it is dev-only synthetic demo data (no prd Neon instance), and
nothing downstream reads its Bronze Publish or Silver Landing tables.

The user chose what to keep: the `bronze_neon` ingestion and its pipeline stay
(the managed Lakeflow Connect pattern, the only one of its kind), and everything
after it goes, provided what is not yet in the patterns bundle is saved there and
the removed pipelines are backed up so they are easy to recover.

## What Changes

- **Remove from the main bundle** (dev only, defined in the `dev` target of
  `cicd/databricks/free.yml` and `standard.yml`): pipelines
  `neon_scd_modeling_python` (`bronze--neon--scd--python--dev`) and
  `silver_landing_neon` (`silver--neon--dev`), and the `bronze_scd`, `silver`
  and verification-of-Landing tasks of `run_neon`; delete
  `src/layers/bronze/neon_publish/` and `src/layers/silver/landing/neon/`,
  `verification/silver_landing_checks/neon.yml`, and the Landing and Publish
  parts of `verification/bronze_checks/neon.yml`. `run_neon` keeps its ingestion
  task and the bronze verification.
- **Keep**: `bronze_neon.*_raw` (4 streaming tables), the pipeline
  `neon_ecommerce_ingestion` (`bronze--neon--lakeflow--dev`), the seed job and
  `run_neon`.
- **Save what the patterns bundle lacks**: it holds the SCD1 snapshot, the SQL
  SCD1 and the SQL SCD2 merge variants, but not the Python snapshot SCD2 flow
  that Neon's `customers_scd2.py` and `products_scd2.py` implement
  (`bronze_publish_scd2_autocdc_snapshot_python`). It is added to
  `references/patterns/` as reference code (never run), with its register entry
  keeping the findings (streaming Auto CDC fails on an upserted source;
  `skipChangeCommits` drops updated rows; switching a flow's source after its
  first run can add spurious versions). The register's "Code" pointers for the
  SCD1 snapshot pattern, which named Neon's files, point to the patterns bundle.
- **Back up what is removed**: `references/backups/neon/` holds the removed
  files unchanged (the two pipelines' definitions, the `run_neon` tasks, the four
  Landing and four Publish source files, the two checks files) and a
  `RECOVERY.md` that says what to copy back, what to deploy and what to run, and
  that the tables rebuild from `bronze_neon`. The main bundle excludes
  `references/**` from its sync, so the backup is never deployed.
- **Drop the tables** (after the PR deploys, by the user's approval): the four
  `bronze_neon_publish.*` streaming tables and the four `silver_landing.neon__*`
  streaming tables, their hidden `__materialization_mat_*` twins and the two
  removed pipelines' `event_log_*` tables. The user deletes the two pipelines
  first (a delete is blocked for the agent), and the stale human-owned copies of
  the Neon pipelines and jobs with them.
- **Not in this change**: clickstream, airroi, acnc Silver Normalised or any
  other candidate; a decision on each is the user's. This change frees about 18
  slots; the investments domain needs the count at or under 488 after it merges
  (456 − 18 + 36 = 474), but gold will need more.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `neon-scd-modeling`: all five requirements removed (the capability is
  retired); the findings move to the design pattern register.
- `pipeline-per-layer`: the neon exception and the "every source has a run job"
  scenario say neon has only its ingestion pipeline.
- `patterns-bundle`: a requirement that the snapshot SCD2 pattern is kept there
  as a reference.

## Impact

- Removed: `src/layers/bronze/neon_publish/python/*` (4 files),
  `src/layers/silver/landing/neon/*` (4 files), two inline pipelines and part of
  one job in the two edition files and the regenerated `databricks.yml`, the
  `neon` Landing checks file and the Publish and Landing parts of the bronze
  checks file.
- Changed: `src/common/design_patterns.yml` (neon keeps only `bronze_neon`),
  `references/docs/registers/design-patterns.md` and `data-sources.md`
  (neon entry), CLAUDE.md (the human-copies note names only what remains),
  `references/patterns/` (new pattern file and pipeline resource), the probes
  register is untouched.
- Table quota: frees 18 slots, dev only. Publish: 4 streaming tables, their 4
  hidden twins and 1 event log (9). Landing: 4 streaming tables, 4 twins and the
  `silver--neon` event log (9). Live count 456 → 438.
- No iac change: nothing in Terraform names these tables or pipelines.
- CI: `run_neon` has `ci_auto_run: "false"`, so no unit runs on merge.

## Cross-repo dependencies

None.

## Model

Sonnet: removing files, moving one pattern into the patterns bundle and writing a
backup follow settled conventions; the drops are the user's.
