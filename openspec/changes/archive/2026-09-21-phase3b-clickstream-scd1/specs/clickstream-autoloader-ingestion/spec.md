## ADDED Requirements

### Requirement: SCD1 modeling in bronze_clickstream_publish
`web_events_scd1` (Python) and `web_events_scd1_sql` (SQL) SHALL exist in
`bronze_clickstream_publish`, built from `bronze_clickstream.web_events_raw`
via Auto CDC keyed by `event_id`, sequenced by `timestamp`, SCD Type 1.
Since `web_events_raw` is append-only, plain streaming Auto CDC SHALL be
used directly in both languages — no snapshot-based workaround is needed
here, unlike Neon's SCD modeling.

#### Scenario: Row counts match the raw table exactly
- **WHEN** both SCD1 pipelines are run against a target with a populated
  `web_events_raw` table
- **THEN** `web_events_scd1` and `web_events_scd1_sql` each have a row
  count matching `web_events_raw` exactly — since events never mutate,
  SCD1 here is a mechanical passthrough with nothing ever overwritten
