## Approach

Layout: the acnc procedure (NAMING.md "Removing a pipeline"; archived
`acnc-two-pipelines` design.md). Timestamps: the bronze full pattern (archived
`correct-platform-timestamps` and `rollout-bronze-full-pattern`). Per source:
(1) a migration job moves each table with
`ALTER ... SET TBLPROPERTIES('pipelines.pipelineId'=...)` as the SP and deletes
the emptied pipelines; (2) the consolidation PR merges the pipeline definitions
and removes the wrapper job; (3) change data feed on the SCD tables, Landing as
streaming tables over the change feed (`land_changes`), and
`migrations/reset_full_load.py` to drop the old Landing views. Tables keep
schemas and names.

## Decisions

- **D1 Normalised standard.** Silver Normalised is rebuilt by the shared
  `normalised` task (`rebuild.py`, keeping `transformed_timestamp` on unchanged
  rows), as for acnc in prd. airroi moves onto it, so its silver pipeline holds
  Landing only, and `src/layers/silver/normalised/pipeline.py` is retired when
  nothing uses it.
- **D2 Landing from an SCD1 table.** `land_changes` gains a `scd2` flag: no
  `__START_AT` rename or `is_current` for an SCD1 source (clickstream, neon
  `orders` and `order_items`); Landing keys on the natural key. Probe P1 checks
  the change feed of an Auto CDC SCD1 target carries the rows needed.
- **D3 ci_auto_run.** neon `"false"` (no prd Neon instance); airroi `"false"`
  (paid); clickstream decided at its stage (prd would get synthetic tables).
- **D4 SCD1 move last**, so it can be cut. The patterns bundle is dev-only; the
  live tables are dropped in dev and prd.

## Per source

- **neon**: dev only. Ingestion is Lakeflow Connect; the SCD2 SQL merge job stays
  exempt. Bronze has no stamping to remove. Landing: customers and products from
  SCD2, orders and order_items from SCD1.
- **clickstream**: `run_clickstream` starts with `generate_clickstream_events`.
  The Auto Loader flow and the Python SCD flow move into one pipeline; check the
  append-only SCD1 stream still reads the Auto Loader table. The SQL twin stays
  exempt.
- **airroi**: bronze 2 pipelines to 1, silver 2 to 1, drop `silver_airroi`; both
  SCD2 views drop the stamping and the per-load `ingested_timestamp`; Normalised
  by D1. One paid dev run (about $0.80) with `verify=true`.

## Probe (dev)

- **P1** Change feed from an Auto CDC SCD1 target (`web_events_scd1`,
  `orders_scd1`) read by a throwaway Landing pipeline: inserts and updates
  arrive, and a second run with no change writes nothing.

## Risks

- Streaming tables cannot be moved while an update is running.
- The dev human pipelines own `silver_landing_clickstream.web_events` and neon
  tables: drop and recreate under the SP, with explicit approval for each drop.
- A task after a gated verification needs `run_if: NONE_FAILED`.

## Staging

Checkpoint after each source: verify, stop, report. Do not start the next
source on a failed verify.

## Inventory: airroi (2026-10-22, read-only)

- **tst**: no airroi tables (the tst catalog was dropped by `free-edition-drop-tst`); tst is out of scope.
- **dev**: every airroi pipeline, job and table is owned by the CI/CD SP; no human-owned copies, so no ownership fix is needed. Tables: bronze_airroi 2 (pipeline ingestion), bronze_airroi_publish 2 (scd), silver_landing_airroi 2, silver_normalised_airroi 7.
- **prd**: bronze_airroi 2 and bronze_airroi_publish 2 exist (ingestion and scd pipelines, SP-owned); silver_landing_airroi and silver_normalised_airroi are empty (silver never ran in prd).
- **Pipelines to merge**: bronze ingestion + scd (dev, prd), silver landing + normalised (dev, prd). Jobs: `run_airroi` (`ci_auto_run: "false"`), `silver_airroi` (to remove), `verify_bronze` for airroi; all exist in dev and prd.
- **Consequence**: the table-move migration applies to bronze in dev and prd, and to silver in dev only. In prd the silver pipelines own no tables, so they are simply replaced.
