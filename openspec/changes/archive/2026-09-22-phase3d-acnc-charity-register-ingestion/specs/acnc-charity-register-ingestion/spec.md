## Purpose

Ingests the ACNC (Australian Charities and Not-for-profits Commission)
Charity Register into `bronze_acnc` via a reusable custom PySpark Data
Source connector generic over any CKAN portal's `datastore_search` API, and
models it as SCD1/SCD2 in `bronze_acnc_publish` — formalizing the custom
Python/API ingestion pattern 3c (UNGM) proved out into a genuinely reusable
connector, per Phase 3d.

## ADDED Requirements

### Requirement: Reusable CKAN data source connector
A registerable Spark data source (`spark.dataSource.register()`) SHALL
exist that is generic over any CKAN portal's `datastore_search` REST API —
schema inferred from the target resource's own field metadata, not
hardcoded to any one dataset's fields. The connector's classes SHALL be
defined inline in the pipeline file that registers them, not in
`src/common/` — custom Spark data source classes are cloudpickled for
execution in a separate worker process that does not inherit the driver
notebook's `sys.path` fix, confirmed via a real `ModuleNotFoundError`.

#### Scenario: Schema inference matches the source's real fields
- **WHEN** the connector's `schema()` is called with `resource_id` set to
  the ACNC Charity Register's CKAN resource id
- **THEN** the resulting `StructType` includes `ABN`, `Charity_Legal_Name`,
  and the rest of the known field list, with types mapped from CKAN's own
  field metadata

### Requirement: Partitioned reads
The connector's `DataSourceReader` SHALL split reads into offset-range
partitions (one `datastore_search` call per partition), not a single
sequential pull, honoring an optional `row_limit` option that caps total
rows read.

#### Scenario: Partition count reflects row_limit
- **WHEN** the connector is invoked with `row_limit=500` and the default
  `page_size`
- **THEN** exactly one partition is produced
- **WHEN** the connector is invoked with no `row_limit` against the full
  ACNC dataset (~66k rows) and the default `page_size`
- **THEN** more than one partition is produced, and the total rows read
  across all partitions equals the source's total row count

### Requirement: Row-limited dev/tst, full prd
`charity_register_raw` SHALL be pulled with `row_limit=500` when deployed to
`dev` or `tst`, and with no row limit (full dataset) when deployed to `prd`.

#### Scenario: Dev and tst are row-limited
- **WHEN** the pipeline is deployed and run against `dev` or `tst`
- **THEN** `charity_register_raw` has exactly 500 rows

#### Scenario: Prd pulls the full dataset
- **WHEN** the pipeline is deployed and run against `prd`
- **THEN** `charity_register_raw`'s row count matches the ACNC Charity
  Register's full current size

### Requirement: Full-refresh batch ingestion into bronze_acnc
`charity_register_raw` SHALL be a Materialized View that re-fetches the
current dataset (subject to `row_limit`) on every run — the source has no
incremental cursor, so full-refresh batch pull is the correct approach.

#### Scenario: Pipeline run lands data
- **WHEN** the pipeline is run against a target
- **THEN** `<catalog>.bronze_acnc.charity_register_raw` exists and is
  populated

### Requirement: Quarantine for un-trackable rows
Charities with a `NULL` `ABN` SHALL NOT be silently dropped. A public
`charity_register_quarantine` table in `bronze_acnc` and a private
`charity_register_valid` view SHALL both read `charity_register_raw` with
complementary conditions (`ABN IS NULL` / `ABN IS NOT NULL`), via
`@dp.expect_or_drop`, so every raw row lands in exactly one of them.

#### Scenario: Every raw row is accounted for
- **WHEN** `charity_register_raw`, `charity_register_quarantine`, and
  `charity_register_valid` are all populated from the same run
- **THEN** `charity_register_raw`'s row count equals
  `charity_register_valid`'s row count plus `charity_register_quarantine`'s
  row count exactly

### Requirement: SCD1/SCD2 modeling, Python only
`charity_register_scd1` and `charity_register_scd2` SHALL exist in
`bronze_acnc_publish`, built via `create_auto_cdc_from_snapshot_flow`
against the private `charity_register_valid` view (not
`charity_register_raw` directly, since NULL-ABN rows must be excluded
first), keyed by `ABN`. No SQL equivalent SHALL be built for this pattern.

#### Scenario: SCD tables match the valid (non-quarantined) row count on initial load
- **WHEN** the SCD pipeline is run after `charity_register_raw` and
  `charity_register_quarantine` are populated
- **THEN** `charity_register_scd1` and `charity_register_scd2` each have a
  row count matching `charity_register_raw`'s row count minus
  `charity_register_quarantine`'s row count exactly

### Requirement: Standing verification suite
A `verification/` suite SHALL exist checking (at minimum) that
`charity_register_raw` is populated and that `charity_register_scd1`/
`charity_register_scd2` row counts match `charity_register_raw` minus
`charity_register_quarantine`, chained into one job
(`verify_acnc_charity_register`) so the pattern can be re-checked on demand.

#### Scenario: Verification job proves the pattern still works
- **WHEN** `verify_acnc_charity_register` is run
- **THEN** all its tasks complete successfully, or the job fails clearly at
  the specific task that found a problem
