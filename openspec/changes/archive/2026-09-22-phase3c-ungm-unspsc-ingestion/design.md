## Context

See proposal.md - Why. Third ingestion pattern, deliberately different from
3a (managed connector) and 3b (file-drop): no native Databricks connector
exists for a plain public REST API, so this is hand-written Python inside a
Lakeflow Declarative Pipeline. Confirmed via real requests against both
UNGM endpoints before any design work started: no auth, no pagination,
~13,335 records / ~1.4MB for production, a slightly smaller snapshot on
test — same flat shape (`Id`, `ParentId`, `UNSPSCode`, `Title`) on both.

## Goals / Non-Goals

**Goals:**
- A working, verified Python/API ingestion pattern, landing into
  `bronze_ungm.unspsc_public_raw` and modeled into SCD1/SCD2
- `dev`/`tst` isolated from the real production UNGM API via the test
  endpoint; only `prd` ever calls production
- A fetch helper generalized within `ungm` (reusable for a future UNGM
  endpoint), not a generic any-API framework

**Non-Goals:**
- Auth implementation — no UNGM endpoint being built now needs it; only a
  documented placeholder (parameter + comment) exists
- A secret scope for the placeholder token — nothing to protect yet;
  provisioned when a real authenticated endpoint is actually added, not
  speculatively here
- SQL SCD1/SCD2 for this pattern — a deliberate scope decision (SQL SCD1
  would work fine here via the same trivial-passthrough trick Neon used,
  since `unspsc_public_raw` is also "full current state per pull"; SQL SCD2
  would hit the same MERGE-job requirement Neon's did). Skipped by choice,
  not technical necessity, since the dual-language demonstration already
  exists via Neon and repeating it adds little here
- Formalizing this as a reusable Lakeflow connector (Connector SDK) — that
  is explicitly Phase 3d's job, a separate future change

## Decisions

**Endpoint parameterized via a bundle variable, same mechanism as `catalog`.**
A new `ungm_base_url` variable in `databricks.yml`, overridden per target
(`dev`/`tst` → `https://wwwtest3.ungm.org`, `prd` → `https://www.ungm.org`),
threaded into the pipeline via its `configuration` block and read with
`spark.conf.get("ungm_base_url")` — identical pattern to how
`clickstream_catalog` is already threaded through the clickstream pipeline,
not a new mechanism invented for this.

**A Materialized View, not a Streaming Table, for `unspsc_public_raw`.**
The API has no pagination and no cursor/updated-at field — every call
returns the complete current dataset. That is a batch full-recompute, not
an incremental stream; `spark.read`/materialized view is the correct
dataset type per the databricks-pipelines skill's own decision tree
("batch/historical/full scan → Materialized View"), not a Streaming Table
artificially wrapped around a non-streaming source.

**Fetch happens inside the MV's Python function body — driver-side HTTP
call, then `spark.createDataFrame(...)`.**
At ~1.4MB / 13k rows this is trivially small for a driver-side fetch
followed by a single `createDataFrame` call — no need for a custom Spark
DataSource or distributed fetch pattern (that complexity is Phase 3d's
territory, formalizing this as a reusable connector). `requests` is added
as an explicit pipeline environment dependency rather than assumed
pre-installed, matching how `faker`/`psycopg2-binary` are declared
explicitly elsewhere in this repo.

**Auth placeholder: a parameter and a comment, not working code or infra.**
`fetch_ungm_endpoint(base_url, path, auth_token=None)` takes the parameter
and, if a caller ever passes one, would include it as a bearer header —
but nothing in this change ever passes one. A comment documents the exact
retrieval call a future authenticated endpoint would use
(`dbutils.secrets.get("ungm", "api_token")`), matching this project's
existing secret-scope naming convention, without creating that scope now.

**`sys.path` + `${workspace.file_path}`, not `--editable` package install,
for making `src/common` importable — discovered mid-implementation, not
assumed upfront.**
The original assumption (glob-including `src/common/**` alongside the
pipeline's own dataset folder in `libraries` would make it importable) was
wrong, confirmed via a real `ModuleNotFoundError: No module named 'common'`.
Databricks pipelines don't add glob-matched sibling directories to
`sys.path`. The documented fix for shared/importable code
(`--editable ${workspace.file_path}` as a pipeline environment dependency)
needs proper setuptools/`pyproject.toml` package-discovery configuration
this repo doesn't have — building that out correctly on a first attempt
risked more failed runs and wasted Free Edition serverless quota for a
speculative payoff. Used `${workspace.file_path}` directly instead (the
same DAB-native variable the `--editable` pattern relies on internally),
threaded through the pipeline's `configuration` block and inserted into
`sys.path` before the import — no packaging complexity, no code
duplication, works today. Revisit proper package-based installation only if
`src/common` grows enough to justify it.

**UNGM's WAF blocks `requests`' default User-Agent — confirmed reproducible
locally, not just on Databricks.**
The first real pipeline run (after fixing the import) failed with `403
Forbidden` calling `wwwtest3.ungm.org`. Before assuming a Databricks/cloud-IP
block, reproduced the exact same request locally with plain Python
`requests` — also `403`. The same URL via `curl` (different default
User-Agent) returned `200`. This isolated the cause precisely: UNGM's WAF
rejects the `python-requests/x.x.x` User-Agent string specifically, not the
calling IP or anything auth-related. Fixed by setting an explicit
`User-Agent` header in `fetch_ungm_endpoint`.

## Risks / Trade-offs

- [The full dataset is re-fetched and re-materialized on every run, with no
  incremental filtering possible] → Mitigation: accepted — the source
  itself offers no cursor, so this is the correct approach, not a
  performance shortcut; ~1.4MB is trivially cheap to refetch on Free
  Edition serverless.
- [`unspsc_public_raw` production and test snapshots differ slightly (test
  is a smaller subset), so `dev`/`tst` verification runs against different
  data than `prd` would see] → Mitigation: acceptable — the whole point of
  using the test endpoint for `dev`/`tst` is exactly this isolation from
  production data; row-count-based verification checks internal consistency
  (raw vs. SCD tables), not a fixed expected count.

## Migration Plan

Depends on `demo-databricks-iac`'s `phase3c-ungm-schema` landing first (see
proposal.md's cross-repo dependencies). Deploy to `dev`, verify via
`verify_unspsc_pattern`, then promote to `tst`/`prd` the same way prior
patterns were. Rollback: remove the resources from the bundle; the pattern
only ever full-refreshes, no destructive state involved.
