# ungm-unspsc-ingestion Specification

## Purpose
Ingests UNGM's UNSPSC classification data into `bronze_ungm` via a custom
Python/REST-API source (no native connector exists for this), and models
it as SCD1/SCD2 in `bronze_ungm_publish`, demonstrating a third distinct
ingestion pattern alongside Lakeflow Connect (3a) and Auto Loader (3b).

## Requirements

### Requirement: Reusable UNGM fetch helper
`src/common/ungm.py` SHALL provide a function that performs an HTTP GET
against a given UNGM API base URL and path, returning parsed JSON, and
SHALL accept an optional auth token parameter for use by future UNGM
endpoints that require authentication — even though the UNSPSC endpoint
itself needs none. No secret scope SHALL be provisioned for this token
speculatively; its retrieval mechanism SHALL be documented in-code only.

#### Scenario: Helper works against both real endpoints
- **WHEN** the helper is called against `https://wwwtest3.ungm.org/API/UNSPSCs`
  and separately against `https://www.ungm.org/API/UNSPSCs`
- **THEN** both calls succeed and return the expected UNSPSC record shape
  (`Id`, `ParentId`, `UNSPSCode`, `Title`)

### Requirement: Endpoint parameterized per target
The pipeline SHALL read from UNGM's test endpoint
(`wwwtest3.ungm.org`) when deployed to `dev` or `tst`, and from the
production endpoint (`www.ungm.org`) when deployed to `prd`.

#### Scenario: Dev and tst use the test endpoint
- **WHEN** the pipeline is deployed and run against `dev` or `tst`
- **THEN** it reads from `wwwtest3.ungm.org`, not `www.ungm.org`

#### Scenario: Prd uses the production endpoint
- **WHEN** the pipeline is deployed and run against `prd`
- **THEN** it reads from `www.ungm.org`

### Requirement: Full-refresh batch ingestion into bronze_ungm
`unspsc_public_raw` SHALL be a Materialized View that re-fetches the
complete UNSPSC dataset on every run — the source has no pagination and no
incremental cursor/updated-at field, so incremental ingestion is not
possible and full-refresh batch pull is the correct approach, not a
workaround.

#### Scenario: Pipeline run lands data
- **WHEN** the pipeline is run against a target
- **THEN** `<catalog>.bronze_ungm.unspsc_public_raw` exists with a row
  count matching the source API's response for that target's endpoint

### Requirement: SCD1/SCD2 modeling, Python only
`unspsc_public_scd1` and `unspsc_public_scd2` SHALL exist in
`bronze_ungm_publish`, built via `create_auto_cdc_from_snapshot_flow`
against `unspsc_public_raw` directly — not streaming Auto CDC, since this
source is not append-only, and not an intermediate snapshot materialized
view, which is unnecessary (confirmed via a real run against Neon's
equivalent pattern). No SQL equivalent SHALL be built for this pattern.

#### Scenario: SCD tables match source row count on initial load
- **WHEN** the SCD pipeline is run after `unspsc_public_raw` is populated
- **THEN** `unspsc_public_scd1` and `unspsc_public_scd2` each have a row
  count matching `unspsc_public_raw` exactly

### Requirement: Standing verification suite
A `verification/` suite SHALL exist checking (at minimum) that
`unspsc_public_raw` is populated and that `unspsc_public_scd1`/
`unspsc_public_scd2` row counts match it, chained into one job
(`verify_unspsc_pattern`) so the pattern can be re-checked on demand.

#### Scenario: Verification job proves the pattern still works
- **WHEN** `verify_unspsc_pattern` is run
- **THEN** all its tasks complete successfully, or the job fails clearly at
  the specific task that found a problem
