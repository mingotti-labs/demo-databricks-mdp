## Context

See proposal.md - Why. Roadmap Phase 3d originally scoped this as
"formalize [UNGM] as a reusable connector via the Lakeflow connector SDK."
Two things changed shape during brainstorming, both explicitly decided with
the user before implementation:

1. **Source**: ACNC's Charity Register (data.gov.au CKAN Data API) instead
   of re-using UNGM. Confirmed via real requests before design work started:
   public, no auth, `datastore_search` REST API (`resource_id` +
   `limit`/`offset` → JSON `{fields, records}`), 66,363 records, natural key
   `ABN`, updated weekly as a full snapshot (no incremental cursor) — same
   WAF-blocks-default-UA behavior as UNGM's endpoint.
2. **Mechanism**: "Lakeflow connector SDK" turned out to name two different,
   real things, both investigated before choosing:
   - Databricks Labs' **Community Connectors** framework
     (`databrickslabs/lakeflow-community-connectors`): a `LakeflowConnect`
     interface (`list_tables`/`get_table_schema`/`read_table_metadata`/
     `read_table`), external repo + CLI tooling, publishes into Databricks'
     "Community connectors" UI picker. Compiles down to the Spark Python
     Data Source API internally. No stated Free Edition/serverless support,
     and deploys outside this repo's DAB/OpenSpec workflow entirely.
   - The **PySpark Custom Data Source API** directly
     (`pyspark.sql.datasource.DataSource`/`DataSourceReader`,
     `spark.dataSource.register()`) — what Community Connectors wraps
     internally. Same underlying SDK, zero external tooling, deploys exactly
     like every other pipeline in this repo.

   Chosen: the direct API. Confirmed no platform blocker either way — this
   repo's pipelines already default to environment version 3/4, comfortably
   above the "serverless environment version 2" minimum the Custom Data
   Source API requires (confirmed via Databricks docs, not assumed).

## Goals / Non-Goals

**Goals:**
- A genuinely reusable CKAN connector — works against any CKAN portal's
  dataset by `base_url`/`resource_id` config, not hardcoded to ACNC's field
  list
- Real partitioned/parallel reads via `DataSourceReader.partitions()`, not a
  single sequential pull — this is the concrete capability the Custom Data
  Source API adds over what a Materialized-View-plus-`requests`-call
  (UNGM's pattern) already does
- `charity_register_raw` landing into `bronze_acnc`, modeled into
  SCD1/SCD2 in `bronze_acnc_publish`, same shape as every other source

**Non-Goals:**
- Databricks Labs' Community Connectors framework — a real alternative,
  explicitly not chosen (see Context above)
- A second real CKAN dataset as a reusability proof — genericity is
  demonstrated by the connector's design (config-driven schema inference,
  no ACNC-specific code), not by standing up a second consumer speculatively
- Auth of any kind — the ACNC Charity Register is fully public, no token,
  no placeholder needed (unlike UNGM, which documented a placeholder for a
  plausible future authenticated endpoint; no such plan exists here)
- SQL SCD1/SCD2 for this pattern — same scope decision UNGM made, for the
  same reason (the dual-language demonstration already exists via Neon)

## Decisions

**Schema inferred from CKAN's own field metadata, not hardcoded.**
`CkanDataSource.schema()` issues one `datastore_search?resource_id=...&limit=1`
call and reads the `fields` array CKAN returns (`{id, type}` per column),
mapping `text`→`StringType`, `int`→`LongType`, `float`→`DoubleType`,
`timestamp`→`TimestampType`, `bool`→`BooleanType`, anything else→`StringType`.
This is what makes the connector genuinely reusable across CKAN datasets —
a new dataset works by changing `resource_id`, no code change.

**Partitioning by offset range.**
`partitions()` reads `result.total` from the same metadata call (capped by
`row_limit` if the option is set), and returns one `InputPartition` per
`page_size`-row offset range (default `page_size=1000`). `read(partition)`
issues one `datastore_search` call per partition. At `prd`'s full ~66k rows
that's ~67 parallel partitions; at `dev`/`tst`'s `row_limit=500` that's 1.

**`acnc_row_limit`, not a separate test endpoint, controls dev/tst blast
radius.**
ACNC/data.gov.au is a single public production dataset — there is no
sandbox to point dev/tst at the way UNGM's `wwwtest3.ungm.org` provided.
Explicitly decided with the user: dev/tst use `row_limit=500` (via a bundle
variable, empty/unset for `prd`) rather than pulling the full dataset in
every environment on every run. Full pulls are cheap (66k rows, no auth, no
cost) — this is about keeping lower-env iteration fast, not a safety
requirement.

**CSV resource, not XLSX.**
Both `datastore_active` resources on the ACNC dataset support
`datastore_search`; the CSV resource (`8fb32972-24e9-4c95-885e-7140be51be8a`)
is used since it's the more standard/lightweight of the two identically-
shaped resources.

**Materialized View, not Streaming Table, for `charity_register_raw`.**
Same reasoning as UNGM's `unspsc_public_raw`: `datastore_search` has no
cursor/updated-at field, every pull is a full current snapshot — a batch
full-recompute, not an incremental stream.

**Connector classes defined inline in `charity_register_raw.py`, not
`src/common/` — discovered mid-implementation, not assumed upfront.**
The original design (this section, before implementation) assumed the
`sys.path` + `${workspace.file_path}` mechanism `unspsc_public_raw.py`
established would carry over directly. It didn't: the first real run
failed with `ModuleNotFoundError: No module named 'common.ckan'`, even
though the exact same sys.path fix was in place. Root cause, confirmed via
Databricks Community reports of the identical failure: custom Spark data
source classes are cloudpickled and reconstructed in a separate worker
process for execution, and that process does not inherit the driver
notebook's `sys.path` modification — unlike UNGM's `fetch_ungm_endpoint`
call, which only ever runs driver-side inside the MV body, never
serialized elsewhere. Fixed by moving `CkanDataSource`/
`CkanDataSourceReader`/`_datastore_search`/`_CKAN_TYPE_MAP` directly into
`charity_register_raw.py` — cloudpickle handles notebook-scope
(`__main__`-like) classes by value, not by reference to an external
module, so nothing needs importing on the worker side. This means the
connector isn't literally shared/importable across files the way
`ungm.py`'s helper is; a future second CKAN dataset would copy this file's
connector block. Genericity is still real — demonstrated by config-driven
behavior (`base_url`/`resource_id`), not by cross-file reuse.

**Same WAF User-Agent fix as UNGM, applied proactively this time.**
Confirmed via a real request during design (not discovered via a pipeline
failure this time): data.gov.au's CKAN API returns `403` to `requests`'
default User-Agent and `200` to a browser-like one. The connector sets an
explicit `User-Agent` header from the start.

**Quarantine pattern for NULL-ABN rows — discovered via a real query
against the deployed `dev` table, not anticipated in the original design.**
The first `charity_register_raw` run (500 rows, `dev`) showed 489 distinct
`ABN`s among 500 rows. Investigated before assuming a connector bug: a
`GROUP BY ABN HAVING COUNT(*) > 1` query showed the "duplicate" was 11
rows sharing a blank-looking `ABN`; a follow-up `IS NULL` check confirmed
these are genuinely `NULL`, not empty string; a `datastore_search_sql`
count against the full dataset confirmed ~605 of ~66,363 records
dataset-wide (mostly Private Ancillary Funds — real charities the ACNC
simply doesn't assign/disclose a public ABN for). Since `ABN` is the
chosen SCD key, these rows have no stable identity for
`create_auto_cdc_from_snapshot_flow` to track. Explicitly decided with the
user (offered two options: exclude-from-SCD-with-visibility vs. a
synthetic fallback key): a quarantine pattern — two datasets read
`charity_register_raw` with complementary `@dp.expect_or_drop`
conditions, so every raw row lands somewhere rather than vanishing.
`charity_register_quarantine` (public, in `bronze_acnc`, `ABN IS NULL`)
makes the exclusion visible and queryable; a **private**
`charity_register_valid` view (`private=True`, in the SCD modeling
pipeline, `ABN IS NOT NULL`) is the actual `source` for
`charity_register_scd1`/`charity_register_scd2`'s
`create_auto_cdc_from_snapshot_flow`. `charity_register_valid` being
private and pipeline-internal (not published to UC) mirrors the "hide
intermediate views that only feed another flow" precedent from the
snapshot cleanup — the difference is this one does real filtering work,
so it's a justified intermediate dataset, not a leftover wrapper.
Confirmed via a real row-count check after both pipelines ran:
`raw(500) = scd1(489) + quarantine(11)` exactly.

## Risks / Trade-offs

- [The Custom Data Source API is a comparatively new Spark/Databricks
  surface] → Mitigation: confirmed the environment-version prerequisite
  before design, not after a failed run; the minimal example from
  Databricks' own docs was verified against the current API shape
  (`DataSource.name()`/`schema()`/`reader()`, `DataSourceReader.read()`/
  `partitions()`) before writing ACNC-specific code.
- [67 partitions each making their own HTTP call to a public government API
  could look like scraping/abuse] → Mitigation: `page_size=1000` keeps total
  request count low (~67 for a full `prd` run, weekly), well within normal
  interactive use of a public open-data API; the explicit `User-Agent`
  header identifies real client behavior rather than masking it.

## Migration Plan

Depends on `demo-databricks-iac`'s `phase3d-acnc-schema` (already merged —
see proposal.md's cross-repo dependencies). Deploy to `dev`, verify via
`verify_acnc_charity_register`, then promote to `tst`/`prd` the same way
prior patterns were. Rollback: remove the resources from the bundle; the
pattern only ever full-refreshes, no destructive state involved.
