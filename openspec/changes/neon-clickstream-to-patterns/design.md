## Context

The patterns bundle (`references/patterns/`, own `databricks.yml`, dev target only) holds
deployable reference implementations that are not part of any source's flow. A human may
deploy it locally (the main-bundle hook does not apply). Its pipelines write to the
dev-only schemas `pattern_bronze` and `pattern_bronze_publish`. Today three of its patterns
read live main-bundle tables (`bronze_neon.customers_raw`, `bronze_clickstream.web_events_raw`).

Quota scan, 2026-11-04 (`references/poc/table-cleanup/counts.txt`): dev 253, prd 229.
`bronze_neon` 9; `bronze_clickstream` 3, `bronze_clickstream_publish` 2,
`silver_landing.clickstream__web_events` 2 (plus its event log if any).

## Goals / Non-Goals

**Goals:** free the dev slots; keep both examples deployable, named for what they show,
with written steps to deploy and remove them; validate the patterns bundle in CI.

**Non-Goals:** iac changes; moving patterns that are already live in another source;
running the patterns in prd.

## Decisions

### D1. Move, not back up
A backup in `references/backups/` is never validated or deployed. The patterns bundle is
both. Rejected: keeping the sources in the main bundle (slots), backups only (stale, cannot
be run to look at).

### D2. Names
Register ids follow `<layer>_<technology>_<variant>_<language>`.
- neon: `bronze_lakeflow_query_postgresql` (Lakeflow Connect query-based connector;
  the source database takes the language's place, since the pipeline is YAML only).
  Resource key `pattern_bronze_lakeflow_query_postgresql`, display
  `bronze--pattern--lakeflow--query--postgresql--${bundle.target}`, tables
  `pattern_bronze.lakeflow_query_postgresql_{customers,products,orders,order_items}`.
- clickstream: `bronze_autoloader_add_new_columns_python` (id unchanged), resource key
  `pattern_bronze_autoloader_add_new_columns_python`, display
  `bronze--pattern--autoloader--python--add_new_columns--${bundle.target}` (same shape as
  the seven), table `pattern_bronze.autoloader_add_new_columns_python`.
- Jobs: `seed--pattern--neon--${bundle.target}`, `generate--pattern--clickstream--${bundle.target}`,
  `verify--pattern--lakeflow--query--postgresql--${bundle.target}`,
  `verify--pattern--autoloader--${bundle.target}`.

### D3. What does not move
`bronze_publish_scd1_autocdc_stream_python` is live in yahoo, rba and fred;
`silver_landing_change_feed_python` in every source. Moving clickstream's copies would add
slots for patterns that can already be read in working code.

### D4. Repoint the dependent patterns
`bronze_publish_scd1_autocdc_stream_sql` reads `pattern_bronze.autoloader_add_new_columns_python`;
`bronze_publish_scd1_materialized_view_sql` and the `bronze_publish_scd2_merge_sql` job
read `pattern_bronze.lakeflow_query_postgresql_customers`. The README gives the run order
(source pattern first).

### D5. Ownership
Pattern resources are deployed and owned by the human. The human owns `neon_dev`
(checked: owner `handsonessential@gmail.com`, SP has `USE_CONNECTION`) and can read the
`neon-postgres` scope; probe P1 confirms the neon pattern runs as the human.

### D6. Removing from the main bundle
Order per NAMING.md "Removing a pipeline": the user deletes the three SP-owned dev
pipelines before the implementation PR merges. Deleting `neon_ecommerce_ingestion`
(Lakeflow Connect) drops `bronze_neon.*_raw` with it; the two regular pipelines leave their
tables, which are dropped with approval (tables, hidden twins, event logs), listed by
`find_orphans.py` afterwards. Jobs are removed by the deploy.

### D7. Freeing slots after a look
`bundle destroy` deletes the pattern pipelines. The Lakeflow Connect tables go with it;
the Auto Loader table and its twin do not, so the README ends with a drop step. Probe P2
confirms both behaviours.

### D8. CI validate
`pr.yml` (generated from `cicd/workflows/<edition>/`, both editions) adds
`databricks bundle validate` run in `references/patterns/`. Validate only: CI never
deploys the patterns bundle.

## Probe results (2026-11-04, dev, as the human)

- **P1** (deploy the patterns bundle from the branch and run both patterns): neon seed wrote
  200/50/500/1,240 rows, the Lakeflow Connect pipeline ran as the human through `neon_dev`,
  `verify--pattern--lakeflow--query--postgresql` passed (counts equal Neon's). The generator wrote
  batch 3 (new field), the Auto Loader pipeline completed, `verify--pattern--autoloader` passed
  (800 rows, 600 with `device_type`). The pattern pipelines used 9 slots; quota went 483 to 492.
- **P2** (`bundle destroy`): 19 resources deleted. The 4 neon pattern tables went with their
  pipeline, but their hidden twins stayed (4 orphans); the Auto Loader table and its twin stayed.
  Both were dropped with approval (`references/poc/table-cleanup/drop_p2.txt`), so the README's
  remove steps must include dropping the twins `find_orphans.py` lists.

## Risks / Trade-offs

- [The Lakeflow Connect pattern needs a live Neon branch] -> the README says so; if Neon's
  free project is ever deleted, the pattern still validates but cannot run.
- [Pattern names in the register change] -> UC tags on dropped tables go with them; the
  `tag--pattern` job tags the new tables.

## Migration Plan

1. P1, P2 in dev as the human (deploy patterns bundle from the branch, run, check, destroy, drop).
2. User deletes the three dev pipelines; drops approved; `find_orphans.py` shows none.
3. Implementation PR (draft, deploy-dev), ready, merge. Quota API re-read.

Rollback: revert the PR and run `run_neon` / `run_clickstream` (`generate=true`) again;
data is synthetic.

## Open Questions

None.
