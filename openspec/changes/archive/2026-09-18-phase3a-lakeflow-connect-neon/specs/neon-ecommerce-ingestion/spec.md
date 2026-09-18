## ADDED Requirements

### Requirement: Seed data
Synthetic e-commerce data (customers, products, orders, order_items — referential
integrity preserved) SHALL be generated with the `Faker` library and written to the
Neon `dev` branch. Every table SHALL include an `updated_at` column.

#### Scenario: Seed job populates Neon dev
- **WHEN** the `seed_neon_ecommerce` job is run
- **THEN** all four tables exist in Neon `dev`, each with non-zero rows, and each
  row has a valid `updated_at` value

### Requirement: Query-based ingestion into bronze_neon
An ingestion pipeline SHALL land each seeded table into
`<catalog>.bronze_neon.<table>` using Lakeflow Connect's query-based architecture
pattern (not CDC/gateway), referencing the `neon_dev` UC Connection and each
table's `updated_at` column as its cursor.

#### Scenario: Pipeline run lands data
- **WHEN** `neon_ecommerce_ingestion` is run against the `dev` target after the
  seed job has populated Neon
- **THEN** `mdp_dev.bronze_neon.customers`, `.products`, `.orders`, and
  `.order_items` all exist with row counts matching the seed data

### Requirement: Delete-blindness is a documented, accepted limitation
The ingestion pipeline SHALL NOT configure `deletion_condition` or any other
delete-tracking mechanism. Hard deletes on the Neon source SHALL NOT be reflected
in `bronze_neon`. This SHALL be documented, not left as an undiscovered gap.

#### Scenario: Documented in CLAUDE.md
- **WHEN** this repo's CLAUDE.md is read
- **THEN** it states that `bronze_neon` does not reflect source-side hard deletes,
  and why

### Requirement: New source tables require an explicit pipeline change
The ingestion pipeline SHALL list each source table explicitly (not ingest the
Neon `public` schema as a whole). A new table added on the Neon source SHALL NOT
be ingested until a corresponding `table:` object is added to the pipeline and
redeployed.

#### Scenario: New table is not auto-ingested
- **WHEN** a new table is added to the Neon `dev` branch without a corresponding
  change to `neon_ecommerce_ingestion.pipeline.yml`
- **THEN** the pipeline run completes without ingesting that table, and no error
  is raised for its absence

### Requirement: Standing verification suite
A `verification/` suite of Databricks notebooks SHALL exist, checking (at minimum)
UC Connection liveness, Neon seed data integrity, and `bronze_neon` row-count
parity with the source — chained into one job so the full pattern can be
re-checked on demand, separate from `tests/` (which covers `src/common/` only via
pytest, with no live-environment dependency).

#### Scenario: Verification job proves the pattern still works
- **WHEN** `verify_neon_ecommerce_pattern` is run
- **THEN** all three of its tasks (connection, seed data, ingestion parity)
  complete successfully, or the job fails clearly at the specific task that found
  a problem
