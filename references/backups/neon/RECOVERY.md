# Neon Bronze Publish and Silver Landing: backup and recovery

Removed by openspec change `neon-publish-cleanup` (2026-11) to free 18 table
slots in the 500-table metastore. Neon is dev only (no prd Neon instance).
`bronze_neon.*_raw` and its Lakeflow Connect pipeline were kept; everything that
read them was removed. This folder holds the removed files unchanged. The main
bundle excludes `references/**`, so nothing here is deployed.

## What was removed

| Backup path | Original path |
|---|---|
| `src/layers/bronze/neon_publish/python/*.py` | same (4 files: `customers_scd2`, `products_scd2`, `orders_scd1`, `order_items_scd1`) |
| `src/layers/silver/landing/neon/*.py` | same (4 files) |
| `verification/bronze_checks/neon.yml` | same |
| `verification/silver_landing_checks/neon.yml` | same |
| `design_patterns.neon.yml` | the `neon:` entry of `src/common/design_patterns.yml` |
| `cicd/<edition>/pipelines_removed.yml` | pipelines `neon_scd_modeling_python` (`bronze--neon--scd--python--<target>`) and `silver_landing_neon` (`silver--neon--<target>`), inline under `targets.dev.resources.pipelines` of `cicd/databricks/<edition>.yml` |
| `cicd/<edition>/run_neon.job.yml` | the whole `run_neon` job as it was, with the `reset`, `bronze_scd`, `verify_bronze`, `silver` and `verify_silver` tasks |

The one pattern that existed only in this code, the Python snapshot SCD2 flow, is
kept in the patterns bundle:
`references/patterns/src/bronze_publish/bronze_publish_scd2_autocdc_snapshot_python.py`.

## Tables dropped (dev)

`bronze_neon_publish.{customers_scd2,products_scd2,orders_scd1,order_items_scd1}`,
`silver_landing.neon__{customers,products,orders,order_items}`, their hidden
`__materialization_mat_*` twins and the `event_log_*` tables of the two pipelines.
Data was synthetic and rebuilds from `bronze_neon`. Landing history (SCD2
versions) restarts from the first rebuild.

## To put it back

1. Copy the files in the table above back to their original paths.
2. In `cicd/databricks/free.yml` (and `standard.yml`), under `targets.dev.resources`:
   paste `pipelines_removed.yml` into `pipelines:` and replace the `run_neon` job
   with `run_neon.job.yml` (drop each file's first comment line). The `standard`
   edition's Landing schema is `silver_landing_neon` and its Landing tables are
   `silver_landing_neon.<entity>`, as its backup file shows.
3. Replace the `neon:` entry in `src/common/design_patterns.yml` with
   `design_patterns.neon.yml`.
4. `uv run python cicd/apply_edition.py`, then `uv run python -m pytest` and
   `databricks bundle validate -t dev`.
5. Deploy by PR (the draft PR deploys to dev as the service principal), then run
   `cicd/run_dev.py neon --profile DEFAULT`. The tables rebuild from
   `bronze_neon`.
6. Update the neon entries in `references/docs/registers/data-sources.md`,
   `references/docs/registers/design-patterns.md` and CLAUDE.md.
