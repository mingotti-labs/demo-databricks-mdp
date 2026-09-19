## Why

Phase 3b needs a second ingestion pattern, deliberately different in shape from
3a's Lakeflow Connect pattern: file-drop ingestion via Auto Loader. Synthetic
clickstream event files, landed in the `s3_clickstream_raw` UC Volume
(`demo-databricks-iac`, `phase3b-clickstream-volume`), get ingested into
`bronze_clickstream.web_events_raw` via a Lakeflow Declarative Pipeline Streaming
Table. Unlike 3a, where schema evolution is automatic, invisible connector
behavior, Auto Loader's schema evolution is an explicit, visible pipeline
setting — this pattern is built specifically to demonstrate and verify that
difference.

## What Changes

- `src/seed_data/generate_clickstream_events.py` — `Faker`-based notebook
  generating batches of web-event JSON files into the volume's
  `web_events/landing/` path; later-generated batches include extra fields
  earlier batches don't have, to exercise Auto Loader's schema evolution rather
  than just claim it works
- `resources/jobs/generate_clickstream_events.job.yml` — serverless job wrapping
  that notebook (`environments:` block: `faker`), deployed to `dev`/`tst`/`prd`
  — each environment generates its own independent synthetic data, no promotion
  between environments
- A new Lakeflow Declarative Pipeline with a Streaming Table `web_events_raw` in
  `bronze_clickstream`, reading via Auto Loader (`cloudFiles`) from the volume's
  landing path, with `cloudFiles.schemaEvolutionMode` set explicitly
  (`cloudFiles.schemaLocation` left unset — pipeline-managed)
- `verification/` additions mirroring the Neon pattern: file-generation check,
  ingestion check, and a schema-evolution check (generate a batch with a new
  field, rerun, confirm the new column lands in the table)
- `resources/jobs/verify_clickstream_pattern.job.yml` chaining those
  verification notebooks into one re-runnable job

## Capabilities

### New Capabilities
- `clickstream-autoloader-ingestion`: Auto Loader-based file-drop ingestion
  pattern landing synthetic clickstream events into `bronze_clickstream`,
  distinct from `neon-ecommerce-ingestion`'s Lakeflow Connect pattern

### Modified Capabilities
(none — `dab-bundle` and `ci-cd-pipeline` already generically cover any resource
type this change adds)

## Cross-repo dependencies

Depends on `phase3b-clickstream-volume` in `demo-databricks-iac` — this change's
Auto Loader pipeline reads from the `s3_clickstream_raw` UC Volume that change
creates, in the `bronze_clickstream` schema it adds. This change should not be
deployed until that one has landed and its volumes are confirmed present in all
three environments.

## Impact

- Adds new job + pipeline resources to the bundle across `dev`/`tst`/`prd`
- Adds `src/seed_data/generate_clickstream_events.py` and new `verification/`
  notebooks
- No changes to existing `neon_ecommerce_ingestion` resources or `bronze_neon`
