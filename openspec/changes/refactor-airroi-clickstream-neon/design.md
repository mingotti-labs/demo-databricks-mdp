## Approach

Reuse the acnc procedure (NAMING.md "Removing a pipeline"; archived
`acnc-two-pipelines` design.md probes P1 to P5). Per source: (1) inventory
ownership and pipeline ids in dev/tst/prd; (2) a migration job moves each table
with `ALTER ... SET TBLPROPERTIES('pipelines.pipelineId'=...)` as the SP and
deletes the emptied pipelines; (3) the consolidation PR merges the pipeline
definitions and removes the wrapper job. Tables keep schemas and names.

## Per source

- **airroi**: 2 bronze to 1, landing + normalised to 1, drop `silver_airroi`.
  `ci_auto_run: "false"` stays (paid API).
- **clickstream**: needs synthetic events first (`generate_clickstream_events`,
  file-drop source), so `run_clickstream` starts with that job. The canonical
  Auto Loader flow (streaming) and the Python SCD flow move into one pipeline;
  check the append-only SCD1 stream still reads the Auto Loader table. SQL
  twin pipeline keeps writing to `bronze_clickstream_publish` (exempt).
- **neon**: dev-only (no tst/prd Neon instance), so `run_neon` runs in dev only.
  Ingestion is Lakeflow Connect, SCD2 SQL merge job stays exempt.
  Display-name-only change for silver.

## Risks

- Streaming tables cannot be moved while an update is running.
- The dev human pipelines own `silver_landing_clickstream.web_events` and neon
  tables: drop and recreate under the SP, with explicit approval for each drop.
- Quota exhaustion mid-run: runs are idempotent; resume the next day.

## Staging

Checkpoint after each source: verify in all environments, stop, report. Do not
start the next source on a failed verify.

## Inventory: airroi (2026-10-22, read-only)

- **tst**: no airroi tables (the tst catalog was dropped by `free-edition-drop-tst`); tst is out of scope.
- **dev**: every airroi pipeline, job and table is owned by the CI/CD SP; no human-owned copies, so no ownership fix is needed. Tables: bronze_airroi 2 (pipeline ingestion), bronze_airroi_publish 2 (scd), silver_landing_airroi 2, silver_normalised_airroi 7.
- **prd**: bronze_airroi 2 and bronze_airroi_publish 2 exist (ingestion and scd pipelines, SP-owned); silver_landing_airroi and silver_normalised_airroi are empty (silver never ran in prd).
- **Pipelines to merge**: bronze ingestion + scd (dev, prd), silver landing + normalised (dev, prd). Jobs: `run_airroi` (`ci_auto_run: "false"`), `silver_airroi` (to remove), `verify_bronze` for airroi; all exist in dev and prd.
- **Consequence**: the table-move migration applies to bronze in dev and prd, and to silver in dev only. In prd the silver pipelines own no tables, so they are simply replaced.
