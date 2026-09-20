# neon-scd-modeling Specification

## Purpose
Models Neon's ingested tables as SCD1 (latest-value) and, for the
dimension-like tables, SCD2 (full history) in `bronze_neon_publish`, in both
Python and SQL, replacing the retired `bronze_neon_history` schema.

## Requirements

### Requirement: SCD1 for all four Neon tables, both languages
`customers_scd1`, `products_scd1`, `orders_scd1`, and `order_items_scd1`
SHALL exist in `bronze_neon_publish`, reflecting the latest value per key
from their respective `bronze_neon.*_raw` source, in both Python (a
Lakeflow Declarative Pipeline using snapshot-based Auto CDC) and SQL (a
plain passthrough materialized view, suffixed `_sql`).

#### Scenario: Row counts match source
- **WHEN** the Python and SQL SCD1 pipelines are run against a target with
  populated `bronze_neon.*_raw` tables
- **THEN** each of the four SCD1 tables (Python and SQL versions) has a row
  count matching its source `*_raw` table exactly

### Requirement: SCD2 for customers and products only, both languages
`customers_scd2` and `products_scd2` SHALL exist in `bronze_neon_publish`,
tracking full history with `__START_AT`/`__END_AT` columns, in both Python
(snapshot-based Auto CDC) and SQL (a hand-rolled two-phase `MERGE` pattern,
suffixed `_sql`, run as a job). `orders` and `order_items` SHALL NOT get
SCD2 — they are transactional, not dimension-like.

#### Scenario: A source update produces two tracked versions
- **WHEN** a row's tracked columns change in the Neon source, the change is
  ingested into `bronze_neon.*_raw`, and the SCD2 flow (Python pipeline or
  SQL merge job) is (re)run
- **THEN** the SCD2 table (Python or SQL) contains two rows for that key —
  the prior version with a non-null `__END_AT` matching the change's
  timestamp, and the new version with a null `__END_AT`

### Requirement: Snapshot-based Auto CDC, not streaming, in Python
The Python SCD flows SHALL use `create_auto_cdc_from_snapshot_flow` against
a batch-read materialized view snapshot of each source table, not
`create_auto_cdc_flow` (streaming). `bronze_neon.*_raw` is upsert-maintained
by Lakeflow Connect, not append-only, so a streaming Auto CDC read against
it fails.

#### Scenario: Streaming Auto CDC against this source fails
- **WHEN** `create_auto_cdc_flow` (streaming) is used with
  `bronze_neon.customers_raw` as `source` and a real update has landed in
  that table
- **THEN** the flow fails with `DELTA_SOURCE_TABLE_IGNORE_CHANGES` —
  confirmed via a real run, not assumed

### Requirement: skipChangeCommits is not an acceptable workaround
`skipChangeCommits` SHALL NOT be used to work around the streaming-source
append-only requirement for these flows, since it silently drops the
updated rows rather than surfacing them — defeating the purpose of SCD
tracking.

#### Scenario: Documented rejection
- **WHEN** this capability's design.md is read
- **THEN** it states that `skipChangeCommits` was considered and rejected,
  with the reasoning (drops updates silently) and the source confirming it
  (Databricks documentation, not assumption)

### Requirement: SQL SCD2 runs as a job, not a pipeline dataset
Since `AUTO CDC INTO` (SQL) supports only streaming sources with no
snapshot-comparison equivalent, and `MERGE` is not valid inside a
declarative streaming-table/materialized-view body, the SQL SCD2 pattern
SHALL run as a Databricks Job with notebook tasks executing the two-phase
`MERGE` directly, not as a `.pipeline.yml` resource.

#### Scenario: SQL SCD2 job runs successfully
- **WHEN** `neon_scd2_merge_sql` is run against a target with populated
  `bronze_neon.*_raw` tables
- **THEN** both its tasks (`customers_scd2`, `products_scd2`) complete
  successfully, and `customers_scd2_sql`/`products_scd2_sql` exist with
  `__START_AT`/`__END_AT` columns
