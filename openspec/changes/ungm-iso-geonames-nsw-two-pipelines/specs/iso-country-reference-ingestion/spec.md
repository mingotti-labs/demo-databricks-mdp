## MODIFIED Requirements

### Requirement: SCD2 modeling, Python only, SCD2-only
`country_codes_scd2` and `subdivision_codes_scd2` SHALL exist in
`bronze_iso_publish`, built by the source's bronze pipeline (`bronze--iso--<target>`, the same pipeline that builds its `_raw` tables) via
`create_auto_cdc_from_snapshot_flow`
against a batch snapshot of their respective source — not streaming Auto
CDC, since neither source is append-only. No SCD1 variant SHALL be built
for either table (a scope decision: low-change-frequency reference data
doesn't need a separate "latest value" table when SCD2's `WHERE __END_AT
IS NULL` gives the same thing). No SQL equivalent SHALL be built for this
pattern.

`country_codes_scd2` SHALL be keyed by `country_code_alpha2` alone.
`subdivision_codes_scd2` SHALL be keyed by `(subdivision_code,
language_code, subdivision_name)` — `subdivision_code` alone is not a
unique key (a subdivision can carry more than one localized name).

Both flows SHALL stamp a `transformed_timestamp` column in an intermediate
dataset immediately upstream of Auto CDC, and SHALL exclude both
`ingested_timestamp` and `transformed_timestamp` via
`track_history_except_column_list` so a rerun with no real source change
creates no spurious SCD2 history.

#### Scenario: SCD2 tables match source row count on initial load
- **WHEN** the bronze pipeline is run after both `_raw` tables are populated
- **THEN** `country_codes_scd2`'s current-row count (`__END_AT IS NULL`)
  equals `country_codes_raw`'s row count (249), and
  `subdivision_codes_scd2`'s current-row count equals the distinct-key
  count of `(subdivision_code, language_code, subdivision_name)` over
  `subdivision_codes_raw` (6,250 — not `subdivision_codes_raw`'s own row
  count of 6,260)

### Requirement: Standing verification suite
A `verification/` suite SHALL exist checking (at minimum): both `_raw`
tables are populated with their expected row counts and carry
`ingested_timestamp`; `subdivision_codes_quarantine` is non-empty and
`raw = distinct_key_count + quarantine_count`; both SCD2 tables' current-row
counts match their expected source count — chained into one job
(`verify_iso_reference_pattern`, displayed as
`verify--bronze--iso--<target>`).

#### Scenario: Verification job proves the pattern still works
- **WHEN** `verify_iso_reference_pattern` is run
- **THEN** all its tasks complete successfully, or the job fails clearly at
  the specific task that found a problem
