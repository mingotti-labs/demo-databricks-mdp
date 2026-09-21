# Naming conventions — demo-databricks-mdp

## Catalog & schema structure

Catalogs: `mdp_dev`, `mdp_tst`, `mdp_prd`

| Layer | Schema pattern | Purpose |
|---|---|---|
| Bronze | `bronze_<source>` | Raw ingestion, append-only |
| Bronze publish | `bronze_<source>_publish` | Validated bronze, safe for downstream reads — includes `<table>_scd1`/`<table>_scd2` tables |
| Silver | `silver_<domain>` | Conformed, domain-modelled (domains TBD) |
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
- Naming for `silver_<domain>` and `gold_*` tables is TBD (domains not yet
  defined) — decide when the first one is actually built, not speculatively here.

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
- **Deployed `name:`** (the display name shown in the UI/API — safe to change
  freely, an in-place rename, not a recreate): `<verb>--<source>--<detail>--${bundle.target}`
  for jobs, `bronze--<source>--<pattern>--${bundle.target}` for pipelines
  (pipelines are bronze-layer data assets; jobs are utility/verification
  actions on a source, hence the different first segment). Double-dash (`--`)
  between every segment, including before `${bundle.target}` — e.g.
  `seed--neon--ecommerce--dev`, `verify--clickstream--autoloader--tst`,
  `bronze--neon--lakeflow--prd`. Distinguishes the same resource key across
  `dev`/`tst`/`prd` and reads cleanly as segments in the UI, unlike a flat
  single-dash string.
