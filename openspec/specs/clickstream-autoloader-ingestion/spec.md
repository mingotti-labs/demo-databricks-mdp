# clickstream-autoloader-ingestion Specification

## Purpose
Ingests synthetic clickstream event files into `bronze_clickstream` via a
Lakeflow Declarative Pipeline Streaming Table using Auto Loader, demonstrating
the file-drop ingestion pattern and its explicit schema-evolution configuration.

## Requirements

### Requirement: Seed data
Synthetic clickstream event files (`event_id`, `session_id`, `user_id`,
`event_type`, `page_url`, `timestamp`, and related fields) SHALL be generated
with the `Faker` library and written as JSON files into the `s3_clickstream_raw`
volume's `web_events/landing/` path. Each environment (`dev`/`tst`/`prd`) SHALL
generate its own independent data — no promotion or copying between
environments.

#### Scenario: Seed job populates the landing volume
- **WHEN** the `generate_clickstream_events` job is run against a target
- **THEN** new JSON files exist under that target's
  `/Volumes/<catalog>/bronze_clickstream/s3_clickstream_raw/web_events/landing/`
  path, each containing valid clickstream event records

### Requirement: Later batches exercise schema evolution
Batches of event files generated after the first SHALL include at least one
field not present in the first batch, so the ingestion pipeline's schema
evolution handling is exercised by real data, not just configured and left
unverified.

#### Scenario: A later batch introduces a new field
- **WHEN** the seed job is run more than once against the same target
- **THEN** at least one field present in a later batch's files is absent from
  the first batch's files

### Requirement: Auto Loader ingestion into bronze_clickstream
A Lakeflow Declarative Pipeline SHALL land clickstream event files into
`<catalog>.bronze_clickstream.web_events_raw` as a Streaming Table using Auto
Loader (`cloudFiles`) reading from the `s3_clickstream_raw` volume's
`web_events/landing/` path. `cloudFiles.schemaEvolutionMode` SHALL be set
explicitly (not left at an implicit default); `cloudFiles.schemaLocation` SHALL
NOT be set, since the pipeline manages it automatically.

#### Scenario: Pipeline run lands data
- **WHEN** `clickstream_autoloader` is run against the `dev` target after the
  seed job has populated the landing volume
- **THEN** `mdp_dev.bronze_clickstream.web_events_raw` exists with row counts
  matching the number of event records across all generated files

### Requirement: New columns are ingested without a pipeline change
Unlike `neon-ecommerce-ingestion`'s explicit-table-list behavior, a new field
appearing in a later batch of clickstream files SHALL be picked up by the
pipeline automatically, without any change to the pipeline definition — this is
the specific behavior `cloudFiles.schemaEvolutionMode` governs, and is verified
empirically, not assumed from documentation.

#### Scenario: New field appears in the target table
- **WHEN** the pipeline is (re)run after a batch containing a new field has
  landed in the volume
- **THEN** `web_events_raw` contains that new column, with `NULL` values for
  rows ingested from batches that didn't have it

### Requirement: Files are not moved or deleted after ingestion
The ingestion pipeline SHALL NOT require moving, archiving, or deleting files
from the landing path after they've been ingested — Auto Loader's exactly-once
guarantee is checkpoint-based, not file-presence-based.

#### Scenario: Landing path still contains already-ingested files
- **WHEN** the pipeline has successfully ingested a batch of files
- **THEN** those files remain present, unmoved and undeleted, in the
  `web_events/landing/` path

### Requirement: Standing verification suite
A `verification/` suite of Databricks notebooks SHALL exist, checking (at
minimum) file generation, ingestion row-count parity, and the schema-evolution
behavior described above — chained into one job so the full pattern can be
re-checked on demand, separate from `tests/`.

#### Scenario: Verification job proves the pattern still works
- **WHEN** `verify_clickstream_pattern` is run
- **THEN** all of its tasks (file generation, ingestion parity, schema
  evolution) complete successfully, or the job fails clearly at the specific
  task that found a problem
