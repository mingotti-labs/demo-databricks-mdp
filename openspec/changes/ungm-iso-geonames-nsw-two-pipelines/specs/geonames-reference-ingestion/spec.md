## MODIFIED Requirements

### Requirement: SCD2 modeling, Python only, SCD2-only
`<table>_scd2` SHALL exist in `bronze_geonames_publish` for all four
tables, built by the source's bronze pipeline (`bronze--geonames--<target>`, the same pipeline that builds its `_raw` tables) via
`create_auto_cdc_from_snapshot_flow` against each
`_raw` table (directly, or via a deduplicating private intermediate if the
key is found not to be unique — see the next requirement). No `_scd1`
variant SHALL be built for any table (a scope decision: low-change-frequency
reference data doesn't need a separate "latest value" table when SCD2's
`WHERE __END_AT IS NULL` gives the same thing). No SQL equivalent SHALL be
built for this pattern.

`country_info` SHALL be keyed by `iso_alpha2`; `admin1_codes` and
`admin2_codes` SHALL be keyed by `code`; `cities` SHALL be keyed by
`geonameid` — each confirmed unique against the real fetched data before
implementation relies on it (row count vs. distinct-key count); a key that
turns out not unique SHALL be corrected using the same evidence-first
approach ISO's `subdivision_code` finding used, not assumed correct from
the column name.

Each flow SHALL stamp a `transformed_timestamp` column in an intermediate
dataset immediately upstream of Auto CDC, and SHALL exclude both
`ingested_timestamp` and `transformed_timestamp` via
`track_history_except_column_list`.

#### Scenario: SCD2 tables match source row count on initial load
- **WHEN** the bronze pipeline is run after all four `_raw` tables are
  populated
- **THEN** each `<table>_scd2`'s current-row count (`__END_AT IS NULL`)
  matches its expected source count (its `_raw` counterpart's row count,
  or the distinct-key count if that table needed deduplication)

### Requirement: Standing verification suite
A `verification/` suite SHALL exist checking (at minimum) that all four
`_raw` tables are populated with their expected row counts and carry
`ingested_timestamp`, and that every table's `_scd2` current-row count
matches its expected source count — chained into one job
(`verify_geonames_reference_pattern`, displayed as
`verify--bronze--geonames--<target>`).

#### Scenario: Verification job proves the pattern still works
- **WHEN** `verify_geonames_reference_pattern` is run
- **THEN** all its tasks complete successfully, or the job fails clearly at
  the specific task that found a problem
