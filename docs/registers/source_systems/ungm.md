# UNGM UNSPSC

The United Nations Global Marketplace's UNSPSC (United Nations Standard
Products and Services Code) classification tree, via a custom Python/REST-API
source — no native Databricks connector. Free, public.

- Base URL: parameterized per target via the `ungm_base_url` bundle variable —
  `dev`/`tst` → `wwwtest3.ungm.org` (test environment), `prd` →
  `www.ungm.org` (production). Same mechanism `catalog` already uses to
  differentiate targets.
- Auth: public endpoint, no auth required for UNSPSC. `src/common/ungm.py`
  takes an optional `auth_token` parameter, unused today but present for a
  future authenticated UNGM endpoint — a comment documents the
  `dbutils.secrets.get("ungm", "api_token")` retrieval such an endpoint would
  use. No secret scope created speculatively.
- **UNGM's WAF blocks `requests`' default User-Agent with a 403** — confirmed
  reproducible even from a local machine (identical URL: curl's default UA
  gets 200, `python-requests`' default UA gets 403). Not an auth issue, not a
  cloud-IP block. Fixed by setting an explicit `User-Agent` header in
  `src/common/ungm.py`. ACNC's data.gov.au runs the same class of WAF —
  discovered here first, applied proactively there.
- Code: `src/common/ungm.py` (small, source-scoped fetch helper, reusable for
  future UNGM endpoints — not a generic any-API framework),
  `src/layers/bronze/ungm/unspsc_public_raw.py`,
  `src/layers/bronze/ungm_publish/unspsc_public_scd1.py`/`unspsc_public_scd2.py`.

## Ingestion in this project

`bronze_ungm.unspsc_public_raw` is a Materialized View that re-fetches UNGM's
**complete** UNSPSC classification tree on every run — the source has no
pagination and no incremental cursor, confirmed via real requests before any
code was written.

- **`src/common/` cross-file imports don't work via `libraries` glob
  inclusion alone** — confirmed via a real `ModuleNotFoundError`
  (glob-including a sibling directory doesn't add it to `sys.path`). Fixed
  with `sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")`
  before the import, where `workspace_file_path` is threaded through the
  pipeline's `configuration` block from DAB's own `${workspace.file_path}`
  variable. This mechanism only applies to plain functions called
  driver-side, not custom Spark DataSource classes — see ACNC's and NSW
  Spatial's docs for that distinction.
- `unspsc_public_scd1`/`unspsc_public_scd2` in `bronze_ungm_publish` —
  Python-only (a scope decision, not a technical necessity for SCD1
  specifically), via `create_auto_cdc_from_snapshot_flow` against
  `unspsc_public_raw` directly (no intermediate snapshot view), since
  `unspsc_public_raw` is "full current state per pull," not append-only.

No platform-added `ingested_timestamp`/`transformed_timestamp` columns yet
(introduced later with AirROI — see NAMING.md's "Platform-added timestamp
columns" and `docs/registers/source_systems/airroi.md`). Apply if this source is
revisited.
