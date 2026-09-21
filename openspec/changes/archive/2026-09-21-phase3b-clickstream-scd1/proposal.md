## Why

Completes `phase3b-bronze-schema-simplification`'s `_raw`+`_publish` pattern
for clickstream: `bronze_clickstream_publish` was created but nothing wrote
to it. Per direct instruction, an SCD1 table belongs there even though
clickstream events never mutate — `_publish` is where governed/secured
access will live later, so every source should flow through it via a
standard mechanism, not just the sources that happen to have real change
semantics.

## What Changes

- `web_events_scd1` (Python) and `web_events_scd1_sql` (SQL): SCD Type 1
  tables in `bronze_clickstream_publish`, built from
  `bronze_clickstream.web_events_raw` via `event_id`-keyed,
  `timestamp`-sequenced Auto CDC
- Unlike Neon's SCD work, plain **streaming** Auto CDC works directly here
  in both languages — `web_events_raw` is genuinely append-only (Auto
  Loader only ever inserts), so none of the snapshot-based workaround
  `phase3b-neon-scd-modeling` needed applies

## Capabilities

### Modified Capabilities
- `clickstream-autoloader-ingestion`: gains a requirement for the SCD1
  modeling step downstream of ingestion

## Cross-repo dependencies

None beyond what `phase3b-clickstream-volume` already depends on.

## Impact

- Adds 2 new pipeline resources (`clickstream_scd_modeling_python`,
  `clickstream_scd_modeling_sql`) across `dev`/`tst`/`prd`
- Writes into `bronze_clickstream_publish` only — no changes to
  `bronze_clickstream` or any other source system
