## Why

Phase 3c adds a third ingestion pattern, deliberately different in shape
from 3a (Lakeflow Connect) and 3b (Auto Loader file-drop): a custom Python
source pulling from a public REST API — UNGM's UNSPSC classification
endpoint. No native Databricks connector exists for this; it's a plain
HTTPS GET wrapped in Databricks Python source code, landing into
`bronze_ungm.unspsc_public_raw` and modeled into SCD1/SCD2 in
`bronze_ungm_publish` using the same snapshot-based Auto CDC pattern
`phase3b-neon-scd-modeling` established.

## What Changes

- `src/common/ungm.py`: a small, source-system-scoped fetch helper —
  `fetch_ungm_endpoint(base_url, path, auth_token=None)` — reusable for
  future UNGM endpoints beyond UNSPSC, not a generic any-API framework.
  Accepts an optional `auth_token` parameter, unused for this endpoint
  (public, no auth) but present so a future authenticated UNGM endpoint can
  reuse the same helper without restructuring it — the retrieval mechanism
  a real token would use (`dbutils.secrets.get("ungm", "api_token")`) is
  documented in-code, not implemented, since no secret scope exists yet and
  none is being created speculatively
- A Lakeflow Declarative Pipeline with a Materialized View
  (`unspsc_public_raw`) doing a full-refresh batch pull via that helper —
  the UNGM UNSPSC endpoint has no pagination and no incremental
  cursor/updated-at field, so every run re-fetches the complete current
  tree (13k+ rows, ~1.4MB, confirmed via a real request against both the
  test and production endpoints)
- Endpoint parameterized per target: `dev`/`tst` → the test endpoint
  (`wwwtest3.ungm.org`), `prd` → production (`www.ungm.org`) — the same
  `configuration`-block threading pattern `clickstream_catalog` already uses
- `unspsc_public_scd1`/`unspsc_public_scd2` (Python only — no SQL
  equivalent is built for this pattern, a deliberate scope decision, not a
  technical necessity for SCD1 specifically) via
  `create_auto_cdc_from_snapshot_flow` against a batch snapshot of
  `unspsc_public_raw`, same pattern as Neon's SCD modeling, since this
  source is also "full current state each pull," not append-only
- A standing verification suite (`verify_unspsc_pattern`), matching every
  other pattern's precedent

## Capabilities

### New Capabilities
- `ungm-unspsc-ingestion`: custom Python/API ingestion of UNGM's UNSPSC
  classification data into `bronze_ungm`, with SCD1/SCD2 modeling into
  `bronze_ungm_publish`

## Cross-repo dependencies

Depends on `demo-databricks-iac`'s `phase3c-ungm-schema` — this change
writes into `bronze_ungm`/`bronze_ungm_publish`, which that change creates.
Should not deploy until that one has landed.

## Impact

- Adds new pipeline resource(s), a verification job, and
  `src/common/ungm.py` to the bundle across `dev`/`tst`/`prd`
- No changes to any existing source system's resources
