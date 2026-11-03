# AirROI Silver Normalised: backup and recovery

Removed by openspec change `remove-airroi-normalised` (2026-11) to free 7 table slots
in the 500-table metastore. AirROI Normalised existed in dev only. Bronze and Silver
Landing for airroi were kept. The main bundle excludes `references/**`, so nothing here
is deployed. The shared builders (`rebuild.py`, `tag.py`, `normalised_spec.py`) stay.

## What was removed

| Backup path | Original path |
|---|---|
| `src/layers/silver/normalised/specs/airroi.yml` | same |
| `resources/jobs/run_airroi.job.yml` | same: the whole job before the change, with the `normalised`, `tag` and Normalised `verify_silver` tasks |
| `design_patterns.airroi.yml` | the `airroi:` entry of `src/common/design_patterns.yml` (it had `silver_normalised_airroi`) |

Decisions and profile: archived change `phase4d-silver-normalised-framework`.

## Tables dropped (dev, by hand on 2026-11-03)

`silver_normalised_airroi.{country,region,locality,district,market_summary,market_metrics_all,value_lineage}`.
They rebuild in full from `silver_landing.airroi__*`; `transformed_timestamp` restarts
at the first rebuild.

## To put it back

1. Copy the spec and the job file back to their original paths.
2. Replace the `airroi:` entry in `src/common/design_patterns.yml` with
   `design_patterns.airroi.yml`.
3. `uv run python -m pytest` and `databricks bundle validate -t dev`.
4. Deploy by PR, then run `cicd/run_dev.py airroi --profile DEFAULT` (costs real API
   money: the bronze fetch runs first).
5. Restore the airroi Normalised lines in `references/docs/registers/data-sources.md`
   and `design-patterns.md`.
