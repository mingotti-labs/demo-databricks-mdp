## Context

See proposal.md - Why. Current acnc layout, per target:

| Pipeline (key) | Default schema | Tables |
|---|---|---|
| `acnc_charity_register_ingestion` | `bronze_acnc` | `charity_register_raw`, `charity_register_quarantine` |
| `acnc_charity_register_scd_modeling` | `bronze_acnc_publish` | `charity_register_scd1`, `charity_register_scd2` (streaming, Auto CDC snapshot targets), private `charity_register_valid` |
| `silver_landing_acnc` | `silver_landing_acnc` | `charity_register` |
| `silver_normalised_acnc` | `silver_normalised_acnc` | ~16 MVs from `normalised/pipeline.py` (spec-driven) |

Jobs: `run_acnc` (bronze ingestion → bronze SCD → `run_job` verify bronze →
`run_job silver_acnc` → `run_job verify_silver_normalised`), `silver_acnc`
(landing → normalised → `tag.py`), `verify_acnc_charity_register`.

Evidence already in hand (2026-10-19 dev probe, scratch pipeline): a fully
qualified `name=` publishes an MV and an Auto CDC snapshot target into a
second schema; `pipelines.reset.allowed=false` on a target whose upstream is
resettable makes a full refresh **fail** (`DLTAnalysisException`), and
Databricks auto-retries the failed update.

Databricks' table move (docs, "Move tables between pipelines"):
`ALTER STREAMING TABLE|MATERIALIZED VIEW <t> SET
TBLPROPERTIES("pipelines.pipelineId"="<destination id>")`. Requires the
caller to be owner and run-as of **both** pipelines, the destination to
exist and have run, the same publishing mode, DBR 16.3+. Private datasets
cannot be moved. The docs do not say whether data, history or flow state
survive.

## Goals / Non-Goals

**Goals:**
- acnc on two pipelines with no table rebuilt and no SCD2 history lost.
- Every unknown proven on scratch pipelines before an acnc table moves.
- A procedure later sources can repeat.

**Non-Goals:**
- Migrating other sources (follow-up changes reuse this design).
- Changing table names, schemas, grants or the normalised framework's
  behaviour.
- Removing the shared `verify_silver_normalised` job (airroi still uses it).

## Decisions

### D1. Reuse one existing pipeline per layer as the destination
Bronze: `acnc_charity_register_ingestion` gains the SCD datasets. Silver:
`silver_normalised_acnc` gains Landing's `charity_register`. Only three
tables move; both destinations already exist and have run (a move
requirement); resource keys are unchanged (NAMING.md: never rename a
deployed pipeline key). The keys no longer describe the whole pipeline, so
the display names carry the meaning: `bronze--acnc--${bundle.target}`,
`silver--acnc--${bundle.target}`.
*Alternative*: two new keys (`bronze_acnc`, `silver_acnc`): clearer keys,
but all ~20 tables move and the destinations must be created and run empty
first.

### D2. Qualified names only for tables outside the default schema
Each merged pipeline keeps its default schema; datasets in it stay
unqualified; the moved ones get a qualified `name=`
(`bronze_acnc_publish.charity_register_scd1`/`_scd2`,
`silver_landing_acnc.charity_register`). Probe P4 decides between a
two-part name (resolved against the pipeline's catalog) and a three-part
name built from a `catalog` pipeline configuration value; the probe used
three parts with a literal catalog, which does not work across targets.
`charity_register_valid` stays private and unqualified: private datasets
are not UC objects, so it is redefined, not moved. Reads stay as today
(`spark.read.table("<schema>.<table>")`); probe P4 confirms an in-pipeline
read resolves to the dataset and orders after it (the normalised spec's
`from: silver_landing_acnc.charity_register`).

### D3. A one-off migration job, run as the service principal
The move must be run by the owner and run-as of both pipelines: the CI/CD
service principal in dev (canonical copies), tst and prd. A bundle job
`migrate_acnc_two_pipelines` runs `migrations/acnc_two_pipelines.py`
(outside `src/`: not medallion code) with the pipeline ids as parameters
(`${resources.pipelines.<key>.id}`, so each target gets its own). It stops
the two source pipelines, then for each of the three tables reads its
current `pipelines.pipelineId` and, if it is not yet the destination, runs
the `ALTER`. Re-running it is a no-op. Anyone can trigger it by job id;
execution identity is the job's (CLAUDE.md).

### D4. Two PRs, migration runs between them
1. PR-A adds the migration job only. It affects no `run_<unit>`, so CI
   deploys it to tst/prd and runs nothing.
2. Run the migration in dev, tst, prd (in that order, checking each).
3. PR-B is the consolidation: merged pipeline code, old pipelines and
   `silver_acnc` and the migration job removed, verify jobs renamed,
   `run_acnc` flattened, docs. Its dev deploy (on PR open) already finds
   dev migrated; after merge CI deploys tst/prd and runs `run_acnc`
   (affected), which is the end-to-end check.

The docs' order is "remove the definition from the source, then ALTER";
here the ALTER comes first and the definitions move in PR-B's deploy, since
CI deploys code on merge. Between the two, nothing runs the old acnc
pipelines (no merge touches acnc). Probe P2 shows what would happen if one
did, so the risk of that window is known, not assumed.

### D5. Jobs
`run_acnc` becomes: bronze pipeline → `run_job verify_acnc_charity_register`
→ silver pipeline → `tag.py` (notebook task, moved from `silver_acnc`) →
`run_job verify_silver_normalised` (`source: acnc`, as today). `silver_acnc`
is deleted. A verify job exists only when it checks something of its own:
acnc's bronze checks are acnc-specific, so that job stays, displayed
`verify--bronze--acnc` with its key unchanged (no recreate, run history
kept). A per-source silver job would only wrap the shared
`verify_silver_normalised`, which already takes `source`, so none is
added.

### D6. Full-refresh protection by refusal
`pipelines.reset.allowed=false` on `charity_register_scd2` only. A full
refresh of the bronze pipeline is then refused (proven), which keeps the
history; normal updates are unaffected. `scd1` stays resettable (it is
rebuilt from the current snapshot anyway).
*Alternative*: also protect the upstream datasets so a full refresh skips
instead of failing: more properties to keep in step, for a rare operation.

## Probes (task group 1, dev, scratch pipelines, `zz_` tables)

- **P1** Move an Auto CDC snapshot SCD2 target with closed versions between
  two scratch pipelines: history intact; an unchanged rerun adds no version;
  one changed key adds exactly one.
- **P2** ALTER while the source still defines the table, then run the
  source: record what happens.
- **P3** Delete the emptied source pipeline: the moved table keeps its rows.
  Observed 2026-10-19 before any probe: deleting the earlier FQN probe
  pipeline left its three tables registered, readable (5 rows) and still
  pointing at the deleted pipeline id. That contradicts CLAUDE.md ("deleting
  a pipeline drops its managed tables"). The delete was
  `databricks pipelines delete <id>` (CLI, no options), and the tables were
  still there ~1.5 h later. CLAUDE.md's evidence is a Lakeflow Connect
  managed ingestion pipeline (`neon_ecommerce_ingestion`), a different
  pipeline type, so neither result generalises yet. PR-B removes pipelines
  by dropping them from the bundle (the deploy deletes them), so P3 tests
  that exact path: a scratch pipeline in a scratch bundle target, emptied by
  a move, then removed from the bundle and deployed.
- **P4** One pipeline: two-part `name=` resolution, and an in-pipeline
  `spark.read.table("<schema>.<t>")` read resolving to the dataset.
- **P5** On the merged-shape probe: full refresh refused, normal update
  runs.

A failed probe stops the change: design and specs are updated (and agreed)
before any acnc resource changes.

## Risks / Trade-offs

- [The move drops history or resets Auto CDC state, versioning every row]
  → P1 first; if it fails, the change stops before PR-A.
- [A migration runs in one environment only, or partly] → idempotent
  notebook; each environment checked (owner pipeline of the three tables)
  before the next.
- [Something runs the old acnc pipelines between migration and PR-B] →
  window kept to one session; P2 tells what it would do.
- [Rollback after PR-B] → not a revert (reverting re-creates the deleted
  pipelines, which would claim tables now owned elsewhere): fix forward.
  Before PR-B, the migration can be reversed by running the same ALTERs
  with the ids swapped.
- [A refused full refresh is auto-retried three times] → noise only;
  documented in CLAUDE.md next to the property.

## Migration Plan

D4. Per environment the check after migration is: each of the three tables
reports its new owner pipeline (`pipelines.pipelineId`), and row and
closed-version counts match the counts taken just before.
