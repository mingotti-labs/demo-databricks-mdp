# Naming conventions — demo-databricks-mdp

## Catalog & schema structure

Catalogs: `mdp_dev`, `mdp_tst`, `mdp_prd`

| Layer | Schema pattern | Purpose |
|---|---|---|
| Bronze | `bronze_<source>` | Raw ingestion, append-only |
| Bronze publish | `bronze_<source>_publish` | Validated bronze, safe for downstream reads — includes `<table>_scd1`/`<table>_scd2` tables |
| Silver Landing | `silver_landing_<source>` | Source-aligned foundational data product, one schema per source — see `references/docs/medallion/silver.md` |
| Silver Normalised | `silver_normalised_<source>` | Source-aligned, restructured to 3NF with extracted entities; values unchanged — see `references/docs/medallion/silver.md` |
| Silver Domain/Marts | `silver_<domain>` | Conformed, domain-modelled (domains TBD — decide when the first one is actually built) |
| Gold | `gold_analytics_gateway` | BI / reporting consumers |
| Gold | `gold_integration_gateway` | Operational / API consumers |
| Gold | `gold_ai_gateway` | ML and GenAI consumers |

Always use 3-part names: `catalog.schema.table`. Never use bare or 2-part references.

## Table naming

- **`<source_table>_raw`** — any table that's a direct, source-faithful landing
  copy (what Lakeflow Connect / Auto Loader writes verbatim, no transformation) —
  in a `bronze_<source>` schema. Makes the "unmodified from source" guarantee
  explicit at the table level, reinforcing what the schema-level purpose above
  already implies. For Lakeflow Connect ingestion pipelines, set this via
  `destination_table` in the `table:` block (defaults to the bare source table
  name otherwise — set it explicitly, don't rely on the default).
  - Retrofitting the name on an already-deployed table (as happened for
    `neon_ecommerce_ingestion`): Lakeflow Connect does not rename/migrate the old
    table — it creates a new one under the new name. Drop the orphaned old table
    manually (`DROP TABLE <catalog>.<schema>.<old_name>`) once the new one is
    confirmed populated.
  - Same convention applies to Auto Loader Streaming Tables — the table name
    itself (the `@dp.table()` / `CREATE OR REFRESH STREAMING TABLE` name) is the
    destination name, so name it `<source_table>_raw` directly (e.g.
    `web_events_raw`); there's no separate `destination_table` setting to set it
    through the way Lakeflow Connect has.
  - Exception: tables in the patterns bundle (`references/patterns/`) are not
    source landings; they are named after their pattern ID without `_raw`
    (`autoloader_rescue_python`).
- **`<table>_scd1`** / **`<table>_scd2`** — modeled tables in a
  `bronze_<source>_publish` schema, built from that source's `_raw` table.
  Replaces the retired `bronze_<source>_history` pattern — see
  `demo-databricks-iac`'s `phase3b-bronze-schema-simplification` design.md.
  Mechanism depends on the source's shape and the language — not
  necessarily `AUTO CDC`/`create_auto_cdc_flow`: for an upsert-maintained
  (not append-only) source like `bronze_neon.*_raw`, Python uses
  `create_auto_cdc_from_snapshot_flow` and SQL SCD1 is a plain passthrough
  materialized view; SQL SCD2 against such a source needs a hand-rolled
  `MERGE`-based job (`<name>_sql` suffix), since `AUTO CDC INTO` has no
  snapshot-comparison equivalent in SQL. See
  `phase3b-neon-scd-modeling`'s design.md for the full reasoning.
- **`<data_source>_public`** — an explicit qualifier for a source system
  with more than one variant of the same data source (e.g. UNGM's UNSPSC:
  `unspsc_public_raw`, alongside a possible future restricted/authenticated
  variant) — not a general-purpose suffix, only used when a real
  distinction exists to make.
- **`<table>_quarantine`** — rows a downstream step can't process, kept
  visible rather than silently dropped, in the same schema as the table
  they were excluded from. At bronze: rows a `_raw` table's SCD modeling
  can't process (e.g. a NULL SCD key), in a `bronze_<source>` schema. At
  Silver Normalised: rows excepted from a declared dependency tolerance, as
  `{entity}_quarantine` in `silver_normalised_<source>`. Built as a Lakeflow expectations
  pair: the quarantine table and its SCD-feeding counterpart both read the
  same `_raw` source with complementary `@dp.expect_or_drop` conditions,
  so every raw row lands somewhere. See ACNC's `charity_register_quarantine`
  (`phase3d-acnc-charity-register-ingestion`'s design.md) for the first
  use of this pattern — introduced when needed, not applied speculatively
  to sources that haven't shown the problem.
- Naming for `silver_<domain>` and `gold_*` tables is TBD (domains not yet
  defined) — decide when the first one is actually built, not speculatively here.

## Silver Normalised tables

In `silver_normalised_<source>` (entity kinds defined in
`references/docs/medallion/silver.md`):

- **Base entity** — keeps its Silver Landing table's name exactly (e.g.
  `charity_register`, `customers`), for one-to-one traceability to Landing.
- **Extracted entity** — the domain name only, singular (e.g. `country`,
  `order_status`); the schema already carries the source. Its natural-key
  column has the same name as the entity.
- **Bridge entity** — `<parent>_<attribute>`, singular attribute (e.g.
  `charity_register_operating_country`).
- **`value_lineage`** — exactly one per source schema, covering all its
  extracted entities.
- **`<entity>_quarantine`** — see Table naming above.
- **`rdm_proposed_match_key`** — the match-hint column on every extracted
  entity; the `rdm_` prefix marks it as a hint for rdm, never used inside
  Silver.

## Platform-added timestamp columns

Two standard lineage columns, added by the platform itself (never sourced from
the upstream API/system). Corrected definition (openspec
`correct-platform-timestamps`, decision register 2026-10-22):

- **`ingested_timestamp`** — the fetch time of the data. On a `_raw` table every
  row, stamped with `current_timestamp()` in the dataset's own query: a full load
  really re-fetches every row. It is never re-stamped past `_raw`.
  - **Bronze full pattern** (`_raw` is a full load): the column changes on every
    row at every load, so it is never part of the snapshot applied to Bronze
    Publish (it would rewrite every current row each run). Auto CDC versions
    each snapshot with the pipeline update's time, written as `__START_AT` on
    the versions it inserts and `__END_AT` on the ones it closes. The SCD2
    table has no platform timestamp columns.
  - Silver Landing sets `ingested_timestamp = __START_AT`: the update that
    created the version (seconds to minutes after the fetch), fixed forever. Aggregating tables (a Silver Normalised
    extracted entity, `value_lineage`) carry the `min()` of their input rows.
- **`transformed_timestamp`** — when this table's own step inserted, modified or
  closed the row. A row the step did not touch keeps its previous value.
  `current_timestamp()` is stamped only where changes are detected, never on a
  full snapshot:
  - Bronze Publish: no column; `__START_AT` and `__END_AT` carry the update times
    (`bronze_publish_scd2_autocdc_full_load_python`);
  - Silver Landing: stamped in a stream that carries only the SCD2 table's
    changed rows (`silver_landing_change_feed_python`);
  - Silver Normalised: a full rebuild keeps the previous stamp on unchanged rows
    and stamps new or changed rows (`silver_rebuild_keep_timestamps_python`).
- **Silver Normalised requires `ingested_timestamp`** on its Landing tables; a
  source without it is retrofitted at bronze just in time.
- **Status**: acnc, ungm, iso, geonames and nsw_spatial follow the corrected
  definition (the bronze full pattern and a change-feed Silver Landing). The
  other sources (neon, airroi, clickstream) still stamp `current_timestamp()` on
  the snapshot (`track_history_except_column_list` stops spurious SCD2 versions
  there, but every current row is still rewritten on every run); each moves in
  its own change. acnc's and iso's and geonames' SCD2 history was not migrated:
  those tables were reloaded from one fetch (2026-10). A source whose `_raw`
  table has no `ingested_timestamp` (ungm, nsw_spatial) needs none: Silver
  Landing takes it from `__START_AT`.

## Volume paths

Files land under `/Volumes/<catalog>/bronze_<source>/<volume>/<data-source>/landing/`
— e.g. `/Volumes/mdp_dev/bronze_clickstream/s3_clickstream_raw/web_events/landing/`.
Volume creation and naming is `demo-databricks-iac`'s responsibility (see its
NAMING.md's "UC Volumes" section); this repo's bundle/pipeline code only ever
references the resulting path. `<data-source>` is one specific data source within
the source system (e.g. `web_events` within the `clickstream` source system) — a
source system can have more than one, each as its own subfolder under the same
volume. `landing/` is reserved for the raw file drop zone; Auto Loader doesn't
require moving processed files out of it for correctness (exactly-once tracking
is checkpoint-based, not file-presence-based) — if a processed/archive step is
ever needed, add a sibling folder via Auto Loader's own
`cloudFiles.cleanSource.moveDestination` rather than restructuring this path.

## Bundle resources

- **Resource key** (the YAML key under `resources.jobs`/`resources.pipelines`):
  `<what>_<detail>`, snake_case (e.g. `seed_neon_ecommerce`,
  `neon_ecommerce_ingestion`). This is DAB's actual resource identity —
  **never rename it on an existing resource** once it's been deployed and has
  real data: DAB treats a changed key as "delete the old, create the new,"
  and deleting a Lakeflow Declarative Pipeline drops its managed tables by
  default (confirmed the hard way — see `demo-databricks-iac`'s CLAUDE.md,
  "CI/CD service principal pipeline execution"). Add a new resource under a
  new key instead of renaming an existing one.
- **Removing a pipeline**: only once it owns no tables. Move each table to
  the pipeline that keeps it (`ALTER STREAMING TABLE|MATERIALIZED VIEW <t>
  SET TBLPROPERTIES('pipelines.pipelineId'='<id>')`, run as the owner and
  run-as of both pipelines, i.e. the CI/CD service principal), then delete
  the emptied pipeline *before* the PR that drops it from the bundle merges:
  `bundle deploy` refuses to delete a pipeline without an interactive
  confirmation or `--auto-approve`, which CI never passes. Read ownership
  from Unity Catalog (`tables get`), not `SHOW TBLPROPERTIES`, which keeps
  the old id for a materialized view. acnc's `acnc-two-pipelines` change is
  the worked example (probes, migration job, results in its design.md).
- **Deployed `name:`** (the display name shown in the UI/API — safe to change
  freely, an in-place rename, not a recreate): `<verb>--<source>--<detail>--${bundle.target}`
  for jobs, `bronze--<source>--<pattern>[--<variant>]--${bundle.target}` for
  pipelines (pipelines are bronze-layer data assets; jobs are
  utility/verification actions on a source, hence the different first
  segment). `<source>` is the source system exactly as in its schema suffix
  (`nsw_spatial`, not `nsw-spatial`); pipeline names stay at source-system
  level and never name the dataset (`bronze--acnc--ingestion--dev`, not
  `bronze--acnc--charity-register-ingestion--dev`). Double-dash (`--`)
  between every segment, including before `${bundle.target}` — e.g.
  `seed--neon--ecommerce--dev`, `verify--bronze--clickstream--tst`,
  `bronze--neon--lakeflow--prd`. Unit jobs (`run_<unit>`, resource key
  prefix `run_`) are named `run--<unit>--${bundle.target}`; their optional
  `ci_auto_run: "false"` tag excludes them from CI runs. A source on one
  pipeline per layer (acnc so far) has `bronze--<source>--${bundle.target}`
  and `silver--<source>--${bundle.target}`, with no pattern segment.
  Reference variants outside a source's official flow use the source system
  `pattern` (`bronze--pattern--autoloader--python--rescue--<target>`):
  clickstream's seven non-canonical Auto Loader pipelines, defined in the
  separate patterns bundle at `references/patterns/`. neon's bronze
  layer keeps two pipelines, as an exception: its ingestion is a managed
  Lakeflow Connect pipeline, which cannot hold the SCD code. The
  `pipeline-per-layer` spec lists every source still pending refactor.
  Verification jobs are named by layer: `verify--<layer>--<source>--${bundle.target}`
  (e.g. `verify--bronze--acnc--dev`), or `verify--<layer>--<check>--${bundle.target}`
  for a check shared by sources, which takes the source as a parameter
  (`verify--silver--normalised--dev`); add one only when it checks something
  no other job does. Distinguishes the same resource key across
  `dev`/`tst`/`prd` and reads cleanly as segments in the UI, unlike a flat
  single-dash string.
