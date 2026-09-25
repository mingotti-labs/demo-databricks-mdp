# CLAUDE.md — demo-databricks-mdp

Conventions for AI-assisted development on this Databricks Modern Data Platform.
This file captures platform-specific decisions; general coding standards are in the
global ~/.claude/CLAUDE.md.

## Platform context

- Databricks Free Edition (serverless compute only, single workspace)
- AWS-hosted workspace: https://dbc-e3197e2d-933b.cloud.databricks.com
- Unity Catalog: one metastore, environments separated by catalog

## Naming conventions

@NAMING.md

## Repository structure

Decided in the `phase2-dab-cicd` OpenSpec change (see its design.md for full rationale):

```
demo-databricks-mdp/
  databricks.yml
  resources/
    jobs/
    pipelines/
    dashboards/
    apps/
  src/
    layers/
      bronze/
        neon/
        neon_publish/
          python/          # snapshot-based Auto CDC vs. bronze_neon.*_raw directly (SCD1 all 4, SCD2 customers/products)
          sql/              # SCD1 only (plain passthrough MVs) -- SCD2 is scd2_merge/, a job not a pipeline
          scd2_merge/       # hand-rolled two-phase MERGE, SQL SCD2's real home
        atlas/
        clickstream/
          python_add_new_columns/   # canonical, only variant ever run
          python_rescue/
          python_fail_on_new_columns/
          python_none/
          sql_add_new_columns/
          sql_rescue/
          sql_fail_on_new_columns/
          sql_none/
        clickstream_publish/
          python/           # SCD1 (mechanical passthrough)
          sql/
        ungm/               # unspsc_public_raw.py (Materialized View, custom API pull)
        ungm_publish/       # SCD1/SCD2 vs. unspsc_public_raw directly, Python only
        acnc/               # charity_register_raw.py + charity_register_quarantine.py --
                            # reusable CKAN custom Spark data source, inlined (see the ACNC
                            # "Sources" entry below for why it isn't in src/common/)
        acnc_publish/       # charity_register_valid.py (private) + SCD1/SCD2 vs. the
                            # private view, Python only
        nsw_spatial/        # property_raw.py -- reusable ArcGIS FeatureServer custom
                            # Spark data source, inlined (same reason as acnc/)
        nsw_spatial_publish/  # SCD1/SCD2 vs. property_raw directly, keyed by
                            # addressstringoid (not propid), Python only
        airroi/             # market_summary_raw.py, market_metrics_all_raw.py --
                            # src/common/airroi.py fetch helper (first paid-API
                            # source), not a reusable connector
        airroi_publish/     # market_summary_scd2.py, market_metrics_all_scd2.py --
                            # SCD2 only, no SCD1
        iso/                # country_codes_raw.py, subdivision_codes_raw.py,
                            # subdivision_codes_quarantine.py -- src/common/iso3166.py
                            # fetch helper, small static-CSV pull, no connector needed
        iso_publish/        # country_codes_scd2.py, subdivision_codes_scd2.py,
                            # subdivision_codes_deduped.py (private) -- SCD2 only, no
                            # SCD1
      silver/
        <domain>/        # domains TBD, per Phase 4
      gold/
        analytics_gateway/
        integration_gateway/
        ai_gateway/
    common/               # shared importable Python modules -- NOT wheel-packaged (no
                          # build-system config yet); see the UNGM "Sources" entry below
                          # for the confirmed sys.path-based import mechanism pipelines use
    seed_data/            # one-off synthetic-data generators, not part of any medallion layer
  tests/
    common/               # mirrors src/common/ only — NOT src/layers/
  verification/           # live-environment functional checks — see "Verification vs validation"
```

- `resources/<type>/`: grouped by resource kind (job/pipeline/dashboard/app), not one flat directory.
- `src/layers/{bronze,silver,gold}/<source-or-domain-or-gateway>/`: mirrors the catalog/schema naming below, not the ingestion pattern or use case. Exception: `bronze/clickstream/`'s subfolders are one per schema-evolution-mode variant (`python_add_new_columns/`, `sql_rescue/`, etc.) — deliberate, isolating each pipeline's `libraries` glob so pipelines never pick up a sibling variant's source file (see `phase3b-clickstream-schema-evolution-variants`'s design.md). Only `python_add_new_columns` is ever actually run; the other 7 exist as documented, deployable reference material.
- `src/common/`: the only part of `src/` that is plainly importable, wheel-packaged Python.
- `src/seed_data/`: synthetic-data generation notebooks — not a medallion layer, not deployed data, just a way to populate a source system for demo/dev purposes. Two shapes so far: truncate-and-reseed for a database source (`seed_neon_ecommerce.py`) vs. append-a-new-batch for a file-drop source (`generate_clickstream_events.py`) — pick the shape that matches how the real source would behave, not one convention for both.
- `tests/` mirrors `src/common/` 1:1 (standard `databricks bundle init` convention). It does not mirror `src/layers/` — pipeline transformation correctness is validated with inline data-quality expectations and `bundle run --refresh`, not pytest.
- `verification/`: Databricks notebooks that check a *deployed* feature actually works against real/synthetic data (connection liveness, row-count parity, referential integrity), chained into a job per pattern. See CONTRIBUTING.md's "Verification vs validation" section — deliberately distinct from `tests/`.

### Resource type ownership: this repo vs. Terraform

The Databricks Asset Bundle resource schema (`databricks bundle schema`, CLI v1.16.1) defines 35 resource types. Not all of them belong in this repo's `resources/`. Split by who owns them:

**Terraform (`demo-databricks-iac`) owns** — Unity Catalog governance and source-DB infra, same family as what Phase 1 already provisions:
`catalogs`, `schemas`, `external_locations`, `secret_scopes`, `secrets`, `volumes`, and (if Lakebase is adopted later) `database_catalogs`, `database_instances`, `postgres_projects`, `postgres_branches`, `postgres_endpoints`, `postgres_databases`, `postgres_roles`, `postgres_snapshot_schedules`, `postgres_catalogs`.

**Not applicable** — Free Edition is serverless-only (see Guardrails below): `clusters`, `cluster_policies`, `instance_pools`.

**This repo (`demo-databricks-mdp`) owns** — workload resources, added under `resources/<type>/` only when a phase actually needs that type (do not pre-scaffold empty folders):
`jobs`, `job_runs`, `pipelines`, `dashboards`, `apps`, `alerts`, `experiments`, `models`, `registered_models`, `model_serving_endpoints`, `quality_monitors`, `genie_spaces`, `vector_search_endpoints`, `vector_search_indexes`, `sql_warehouses`, `postgres_synced_tables`, `synced_database_tables`.

## DAB targets

Three targets in `databricks.yml`, all pointing to the same workspace,
differentiated by catalog:

- `dev` → `mdp_dev`
- `tst` → `mdp_tst`
- `prd` → `mdp_prd`

## Sources

- **Neon Postgres** (serverless, free tier) — relational source. `bronze_neon` is
  populated by `neon_ecommerce_ingestion`, a query-based Lakeflow Connect pipeline
  (not CDC — the gateway architecture needs classic compute, unavailable on Free
  Edition) reading from the Neon `dev` branch via the `neon_dev` UC Connection
  (`demo-databricks-iac`). `dev`-scoped only: no separate `tst`/`prd` Neon
  branch/instance exists yet, so those targets get this pipeline's code on
  promotion but nothing to actually ingest.
  - Seed data (`src/seed_data/seed_neon_ecommerce.py`) is synthetic, generated with
    `Faker`, not a real dataset.
  - Hard deletes on the Neon source are **not** propagated to `bronze_neon` —
    query-based ingestion without `deletion_condition` can't see them (a deleted
    row just stops appearing in query results). Accepted, not a bug.
  - New columns/removed columns on an already-ingested table are handled by
    Lakeflow Connect automatically (new columns backfill as `NULL` for old rows;
    removed columns are marked `inactive`, not dropped — re-adding a same-named
    column afterward fails the pipeline until a full refresh or a manual drop of
    the inactive column). A **new table** is not auto-ingested — this pipeline
    lists tables explicitly; add a `table:` block and redeploy.
  - `bronze_neon_publish` holds `<table>_scd1`/`<table>_scd2` modeling
    (SCD1 for all four tables, SCD2 for `customers`/`products` only),
    replacing the retired `bronze_neon_history` schema. Built in both
    Python and SQL — but **not the same way**: `bronze_neon.*_raw` is
    upsert-maintained (Lakeflow Connect MERGEs changed rows in place via
    `cursor_columns`), not append-only, so streaming Auto CDC
    (`create_auto_cdc_flow`) fails against it with
    `DELTA_SOURCE_TABLE_IGNORE_CHANGES` — confirmed via a real run, not
    assumed. `skipChangeCommits` is not a fix — it silently drops the
    updated rows instead of surfacing them (confirmed via Databricks docs).
    - Python: `create_auto_cdc_from_snapshot_flow` (snapshot comparison,
      not streaming) against `bronze_neon.*_raw` directly — the correct,
      pipeline-native fix. No intermediate snapshot materialized view is
      needed: `source` does not have to be a dataset within the same
      pipeline's own dataflow graph, confirmed via a real run (an earlier
      version of this pattern wrapped the read in one anyway, following the
      Databricks docs' example pattern literally, before this was tested
      and found unnecessary — see `phase3b-scd-snapshot-cleanup`'s
      design.md). **Caution confirmed the hard way**: switching a
      snapshot flow's `source` on an *already-run* flow whose source is a
      Streaming Table can insert spurious duplicate "no-op" versions for
      unchanged rows into the SCD2 table — a full refresh is the fix, and
      it discards prior history in the process. Not an issue for a flow
      that's always pointed at the same source from its first run.
    - SQL SCD1: a plain passthrough materialized view — `bronze_neon.*_raw`
      already is "latest value per key" by construction, no CDC needed.
    - SQL SCD2: `AUTO CDC INTO` is streaming-only in SQL with no snapshot
      equivalent, and `MERGE` isn't valid inside a declarative pipeline
      dataset — so this runs as a **job**
      (`neon_scd2_merge_sql`), not a `.pipeline.yml` resource, using the
      classic two-phase `MERGE` pattern (expire the old version, insert the
      new one). See `phase3b-neon-scd-modeling`'s design.md for the full
      investigation.
- **MongoDB Atlas** (M0 free cluster) — document source
- **Clickstream files** (synthetic, entirely generated by this repo — no real
  upstream system) — file-drop source. `bronze_clickstream.web_events_raw` is
  populated by `clickstream_autoloader`, a Lakeflow Declarative Pipeline
  Streaming Table using Auto Loader, reading JSON event files from the
  `s3_clickstream_raw` UC Volume (`demo-databricks-iac`,
  `phase3b-clickstream-volume`) at
  `/Volumes/<catalog>/bronze_clickstream/s3_clickstream_raw/web_events/landing/`.
  Multi-env, unlike Neon: `dev`/`tst`/`prd` each generate and ingest their own
  independent synthetic data — there's no single upstream branch to be
  dev-scoped against, since the data is fully synthetic either way.
  - Seed data (`src/seed_data/generate_clickstream_events.py`) is synthetic,
    generated with `Faker`; each run appends a new batch rather than
    truncating/reseeding — files accumulate, matching a real file-drop source.
  - Files are never moved or deleted after ingestion — Auto Loader's
    exactly-once guarantee is checkpoint-based, not file-presence-based.
  - `cloudFiles.schemaEvolutionMode` is set explicitly to `addNewColumns` (Auto
    Loader's own default, made visible rather than implicit). A genuinely new
    column in a later batch terminates the in-flight flow once
    (`"... encountered a schema change during execution and terminated"`), and
    Databricks itself starts and completes a new update automatically (cause
    `SCHEMA_CHANGE`) — confirmed empirically, not assumed. The triggering
    `bundle run`/API call that observed the mid-flight cancellation does exit
    non-zero even though the pipeline self-recovers; don't mistake that for a
    real failure.
  - Interview-prep reference: all four `schemaEvolutionMode` values
    (`addNewColumns`/`rescue`/`failOnNewColumns`/`none`) exist as separate,
    independently deployable pipelines, each in both Python and SQL (8
    total), each with its own target table and an in-code write-up of that
    mode's behavior and error/recovery workflow. Only `addNewColumns`
    (Python, the canonical resource above) is ever actually run — the other
    7 are documented from Databricks' own docs, not independently
    re-verified here. See `src/layers/bronze/clickstream/` and
    `phase3b-clickstream-schema-evolution-variants`'s design.md. Production-
    hardening pattern (practitioner-sourced, not official docs — see the
    canonical `python_add_new_columns/web_events_raw.py`'s header for the
    citation): pair `addNewColumns` with `rescuedDataColumn` at bronze as a
    safety net, push schema strictness to silver instead, and treat the
    restart-on-schema-change behavior as a deliberate checkpoint-refresh
    mechanism meant to pair with automatic job retry, not something to
    avoid.
  - `bronze_clickstream_publish.web_events_scd1`/`web_events_scd1_sql`:
    SCD1 modeling downstream of the canonical `web_events_raw`, keyed by
    `event_id`, sequenced by `timestamp`. Exists for downstream-usage
    consistency with every other source's `_publish` schema, not because
    events change — each `event_id` only ever appears once, so this is a
    mechanical passthrough. Unlike Neon's SCD pipelines, plain **streaming**
    Auto CDC works directly here in both languages, no snapshot-based
    workaround needed — `web_events_raw` is genuinely append-only (Auto
    Loader only ever inserts). Confirmed by actually running both
    pipelines, not assumed from the Neon precedent. See
    `phase3b-clickstream-scd1`'s design.md.
- **UNGM UNSPSC** (Phase 3c) — custom Python/REST-API source, no native
  connector. `bronze_ungm.unspsc_public_raw` is a Materialized View that
  re-fetches UNGM's complete UNSPSC classification tree on every run (the
  source has no pagination and no incremental cursor, confirmed via real
  requests before any code was written). Endpoint parameterized per target
  via the `ungm_base_url` bundle variable: `dev`/`tst` →
  `wwwtest3.ungm.org` (test), `prd` → `www.ungm.org` (production) — the
  same mechanism `catalog` already uses.
  - `src/common/ungm.py`: a small, source-scoped fetch helper, reusable for
    future UNGM endpoints (not a generic any-API framework). Takes an
    optional `auth_token`, unused here (UNSPSC is public) but present for a
    future authenticated endpoint; a comment documents the
    `dbutils.secrets.get("ungm", "api_token")` retrieval such an endpoint
    would use — no secret scope created speculatively.
  - **`src/common/` cross-file imports don't work via `libraries` glob
    inclusion alone** — confirmed via a real `ModuleNotFoundError`
    (glob-including a sibling directory doesn't add it to `sys.path`). Fixed
    with `sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")`
    before the import, where `workspace_file_path` is threaded through the
    pipeline's `configuration` block from DAB's own `${workspace.file_path}`
    variable — the same variable the documented `--editable
    ${workspace.file_path}` shared-package pattern relies on, used directly
    here since that pattern needs setuptools/`pyproject.toml`
    package-discovery config this repo doesn't have yet. See
    `unspsc_public_raw.py`'s header.
  - **UNGM's WAF blocks `requests`' default User-Agent with a 403** —
    confirmed reproducible even from a local machine (identical URL: curl's
    default UA gets 200, `python-requests`' default UA gets 403). Not an
    auth issue, not a cloud-IP block. Fixed by setting an explicit
    `User-Agent` header in `src/common/ungm.py`.
  - `unspsc_public_scd1`/`unspsc_public_scd2` in `bronze_ungm_publish` —
    Python-only (a scope decision, not a technical necessity for SCD1
    specifically), via `create_auto_cdc_from_snapshot_flow` against
    `unspsc_public_raw` directly (no intermediate snapshot view — see
    Neon's entry above), since `unspsc_public_raw` is also "full current
    state per pull," not append-only — same pattern as Neon's SCD
    modeling. Unaffected by the source-Streaming-Table duplication caveat
    above, since `unspsc_public_raw` is a Materialized View, not a
    Streaming Table.
- **ACNC Charity Register** (Phase 3d) — a reusable custom Spark data
  source connector (`CkanDataSource`/`CkanDataSourceReader`, built on
  `pyspark.sql.datasource`, not Lakeflow Connect's managed catalog and
  not Databricks Labs' separate "Community Connectors" repo/CLI — see
  `phase3d-acnc-charity-register-ingestion`'s design.md for why both were
  considered and not chosen), generic over any CKAN portal's
  `datastore_search` REST API (data.gov.au, data.gov.uk, etc.), with the
  ACNC Charity Register as the first real consumer. `bronze_acnc.charity_register_raw`
  is a Materialized View built on `spark.read.format("ckan")...load()`.
  - **The connector's classes live inline in `charity_register_raw.py`,
    not in `src/common/`** — confirmed via a real `ModuleNotFoundError:
    No module named 'common.ckan'` that custom Spark data source classes
    are cloudpickled for execution in a separate worker process that does
    not inherit the driver notebook's `sys.path` fix (the mechanism
    `unspsc_public_raw.py` relies on works there only because that fetch
    is purely driver-side, never serialized to another process). This
    matches reports of the identical failure in the Databricks Community.
    A future second CKAN dataset would copy this file's connector block
    rather than import it.
  - **Schema is inferred from CKAN's own field metadata**, not hardcoded
    to ACNC's fields — one `datastore_search?limit=1` call reads the
    resource's `fields` array and maps CKAN's `text`/`int`/`float`/
    `timestamp`/`bool` types to their Spark equivalents. This, not a
    second real dataset, is what makes the connector "reusable": a new
    CKAN dataset works by changing `resource_id`/`base_url`, no code
    change.
  - **Reads are partitioned by offset range** (`DataSourceReader.partitions()`),
    not a single sequential pull — `page_size` rows per partition (default
    1000), honoring an optional `row_limit` option.
  - **`acnc_row_limit`, not a separate test endpoint, controls dev/tst
    blast radius** — ACNC/data.gov.au is a single public production
    dataset, no sandbox exists the way UNGM's test endpoint provided.
    `dev`/`tst` pull 500 rows; `prd` pulls the full dataset (~66k rows,
    confirmed via the CKAN API before this was built).
  - data.gov.au runs the same class of WAF as UNGM's API — blocks
    `requests`' default User-Agent with a 403, confirmed via a real
    request before any code was written. Fixed the same way, proactively
    this time.
  - **Quarantine pattern**: ~605 of ~66k charities (mostly Private
    Ancillary Funds) have a `NULL` ABN, confirmed via the CKAN SQL
    endpoint (`datastore_search_sql`) before SCD modeling was built — a
    real data-quality condition in the source, not a connector bug. Since
    `ABN` is the SCD key, these rows have no stable identity to track.
    Rather than silently drop them, two datasets read the same
    `charity_register_raw` with complementary `@dp.expect_or_drop`
    conditions: `bronze_acnc.charity_register_quarantine` (public, `ABN
    IS NULL`) keeps them visible and queryable; a **private**
    (`private=True`) `charity_register_valid` view in the SCD modeling
    pipeline (`ABN IS NOT NULL`) feeds `charity_register_scd1`/`scd2`'s
    `create_auto_cdc_from_snapshot_flow`. Unlike the removed `*_snapshot`
    wrapper views (see Neon's entry above), `charity_register_valid` does
    real filtering work, so an intermediate dataset is justified here, not
    a leftover. Verification checks `raw = scd_count + quarantine_count`,
    not raw-equals-SCD exactly.
- **NSW Spatial Services** (Phase 3f) — a second reusable custom Spark
  data source connector (`ArcGisFeatureServerDataSource`/`...Reader`),
  generic over any Esri ArcGIS REST FeatureServer layer, alongside 3d's
  CKAN connector. First consumer: NSW Spatial Services' "Property" layer
  (`portal.spatial.nsw.gov.au`), sourced ultimately from Property NSW's
  Valnet database. `bronze_nsw_spatial.property_raw` is a Materialized
  View built on `spark.read.format("arcgis_feature_server")...load()`.
  - **Connector classes are inline in `property_raw.py`**, applying
    ACNC's `src/common/` lesson proactively — no `ModuleNotFoundError`
    rediscovery needed this time.
  - **Schema inferred from the layer's own `?f=json` metadata**, same
    principle as the CKAN connector's `schema()`. Reads partitioned by
    offset range (`resultOffset`/`resultRecordCount`, ArcGIS REST's
    equivalent of CKAN's `offset`/`limit`).
  - **The connector must discover each FeatureServer's own
    `maxRecordCount`, not assume one** — confirmed via a real first run:
    this server caps `resultRecordCount` at 100, silently truncating a
    larger request instead of erroring, which undercounted the first
    `dev` run's row math (100 rows landed against a `row_limit` of 500).
    Fixed by reading `maxRecordCount` from the same metadata call
    `schema()` already makes and capping `page_size` to it.
  - **The SCD key is `addressstringoid`, not `propid`** — also caught via
    the real first run (486 distinct `propid` among 500 rows), not a
    pre-build check. This layer's actual grain is one row per *address*
    within a property, not one row per property: a unit block has one row
    per unit, all sharing the parent property's `propid`/`gurasid`/
    `principaladdresssiteoid`, differentiated only by `addressstringoid`
    (confirmed unique with zero `NULL`s across the real 500-row `dev`
    sample — not exhaustively checked at full ~4.2M-row scale). No
    quarantine pattern needed — this was a wrong key, not missing/dirty
    data.
  - **`prd` does not pull the full dataset, unlike every other source in
    this project.** The `maxRecordCount` finding means a full ~4.2M-row
    pull would need ~42,259 requests (page_size capped at 100) — ~630x
    ACNC's `prd` request volume. `nsw_property_row_limit` caps `prd` at
    `10000` (100 requests, matching ACNC's `prd` request count) instead
    of pulling everything; `dev`/`tst` use `500`.
  - A `curl`-style `User-Agent` header is set proactively, matching
    UNGM's and ACNC's confirmed WAF pattern — **not independently
    confirmed necessary for this specific server**, since every real
    request against it in this project used that header from the start.
    If it turns out unnecessary, that's a safe no-op, not a false claim.
- **AirROI** (Phase 3h) — this project's **first source with a real,
  paid, authenticated API**. Every prior source is free/public. AirROI
  has no free sandbox; every call costs real money. `bronze_airroi.market_summary_raw`
  pulls four confirmed real markets (Vitória da Conquista/BA, Urubici/SC,
  Tauranga/NZ, and Prado/BA queried with `district="Cumuruxatiba"`) via
  `src/common/airroi.py`'s `fetch_market_summary`, a plain source-scoped
  fetch helper (not a full reusable connector — AirROI is one proprietary
  vendor's API, not a reusable protocol like CKAN/ArcGIS). `market_summary_scd2`
  in `bronze_airroi_publish` is **SCD2 only, no SCD1** — a deliberate
  scope decision (SCD1 would just duplicate SCD2's `WHERE __END_AT IS
  NULL` filter).
  - **Cumuruxatiba has no standalone market on AirROI** — it's a named
    neighborhood within Prado's report, queried as `locality="Prado"` +
    `district="Cumuruxatiba"` (the `market` object's fourth, optional
    field, `NULL` for the other three markets). `district` was confirmed
    genuinely functional, not silently ignored, via a real before/after
    call: `locality="Prado"` alone returns 1,102.7 active listings;
    adding `district="Cumuruxatiba"` returns 360.6 — a real, different
    subset. Both `market_summary_scd2` and `market_metrics_all_scd2` key
    on `_district` alongside `_country`/`_region`/`_locality` so
    Cumuruxatiba can't collide with a hypothetical future Prado-level
    market.
  - **`market_metrics_all_raw`/`market_metrics_all_scd2`** — the
    time-series counterpart to `market_summary`, via
    `fetch_market_metrics_all` against `/markets/metrics/all`. Real
    response shape (confirmed via a live test call, not assumed from
    docs): `{"market": {...}, "results": [...]}`, where `results` is a
    rolling ~12-month window (one trailing month + ~11 forward-looking
    months) of `{date, occupancy, average_daily_rate, revpar, revenue,
    booking_lead_time, length_of_stay, min_nights, active_listings_count}`
    — every metric except `active_listings_count` is a **distribution
    object** (`{avg, p25, p50, p75, p90}`), unlike `market_summary`'s flat
    single values. Landed as one row per `(market, date)`, metric structs
    kept as-is (flattening is a silver concern). SCD2-keyed on
    `_country`/`_region`/`_locality`/`_district`/`date` — unlike
    `market_summary`, the SCD2 need here is tracking how AirROI *revises*
    a given future month's forecast between pulls, not just tracking a
    single evolving "current value" per market. 4 markets × 12 months =
    48 rows/run; every run re-calls the API for all 4 markets (Materialized
    View, always fully recomputed) — 4 × $0.10 = $0.40/run, same cost
    profile as `market_summary_raw`.
  - **`ingested_timestamp`/`transformed_timestamp`** — this source is
    where the platform's two standard lineage timestamp columns were
    introduced (see NAMING.md's "Platform-added timestamp columns").
    `ingested_timestamp` stamped in each `_raw` MV; `transformed_timestamp`
    stamped in a temp view wrapping the `_raw` source before each SCD2
    flow, both excluded via `track_history_except_column_list` — without
    that exclusion, `current_timestamp()`'s per-run difference would make
    Auto CDC think every row changed every run, versioning spuriously.
    Confirmed via a real run: row counts stayed correct (4 / 48 current
    rows) only once the exclusion was in place.
  - **Markets confirmed/dropped based on real evidence, not the original
    prompt's assumptions.** Originated from a pasted AI-generated prompt
    about "AirDNA" and two illustrative Brazilian cities (Salvador/Sumaré);
    AirDNA itself was investigated and rejected (Enterprise-only,
    ~$50K+/year, sales-negotiation-gated). The final three markets were
    each individually verified as clean, non-fragmented entries on
    AirROI's own public site before being used (free to check). Sydney
    was explicitly dropped: its plain `sydney` slug sits alongside 50+
    separate Sydney-suburb pages (Bondi, Surry Hills, Parramatta, etc.),
    strongly indicating a generic/residual bucket, not a real Local
    Government Area or the Greater Sydney metro. Tauranga has one
    accepted minor gap — Papamoa, a real Tauranga suburb, is a separate
    sibling page, likely excluded from `tauranga`'s figures.
  - **Both AirROI's own published request and response examples for
    `/markets/summary` are wrong — confirmed via real calls, not assumed
    correct from docs.** The documented request shape (flat
    `country_code`/`state`/`city` fields) returned a real `422`; the
    actual required shape is a nested `market` object with `country`/
    `region`/`locality` **display names** (not URL slugs). The documented
    response field names (`active_listings`, `average_adr`,
    `average_occupancy`, `average_revpar`, `median_annual_revenue`, etc.)
    also don't match the real response (`active_listings_count`,
    `average_daily_rate`, `occupancy`, `rev_par`, `revenue`,
    `booking_lead_time`, `length_of_stay`, `min_nights`, plus a
    structured `market` map echoing the request) — this project's
    evidence-over-documentation principle held even against the vendor's
    own docs.
  - **SCD key is the flat `_country`/`_region`/`_locality` columns
    `market_summary_raw` carries, not the API's nested `market` map** —
    `create_auto_cdc_from_snapshot_flow`'s `keys=` needs flat columns,
    not a struct/map type.
  - **Real per-call cost is $0.10, not the $0.01 AirROI's general
    pricing page advertises** — confirmed via the user's own observed
    charge, a 10x gap from the headline rate. Worth re-confirming before
    scaling call volume for any future work on this source (e.g. the
    deferred individual-listings endpoint, sized using
    `active_listings_count` from this data once a real limit is chosen).
  - **`revenue`'s exact time period (annual? some other window?) is not
    confirmed** — a rough sanity check against `ADR × 365 × occupancy`
    didn't match closely enough to confidently call it "annual," unlike
    `rev_par`, which does check out closely against `ADR × occupancy`.
  - No per-environment row-limiting, unlike ACNC/NSW property — there's
    no free-tier/smaller-sample concept for a fixed 3-market pull;
    `dev`/`tst`/`prd` all use the same three markets.
- **ISO 3166 country/subdivision reference data** (Phase 3i) — the
  smallest ingestion pattern in the project: two static CSVs from a
  public, unauthenticated GitHub mirror
  (`raw.githubusercontent.com/ipregistry/iso3166`, CC BY-SA 4.0), no
  pagination, no WAF block, no per-environment URL split.
  `src/common/iso3166.py`'s `fetch_iso3166_csv` is a plain
  `requests.get()` + `csv.DictReader`. `bronze_iso.country_codes_raw`/
  `subdivision_codes_raw` are Materialized Views; both stamp
  `ingested_timestamp`. CC BY-SA 4.0 attribution is set as a Unity Catalog
  table `comment` on both `_raw` tables (`@dp.materialized_view(comment=...)`),
  not just a docs note — the first externally-*licensed* (not just
  externally-sourced) dataset in this project.
  - `subdivision_code_iso3166-2` is renamed to `subdivision_code` on
    ingest — the source column name's hyphen isn't a valid identifier on
    its own, and the schema name already implies "ISO 3166-2."
  - **SCD2-only, no SCD1** — a scope decision (not a technical
    necessity): low-change-frequency reference data doesn't need a
    separate "latest value" table when SCD2's `WHERE __END_AT IS NULL`
    gives the same thing. `country_codes_scd2`/`subdivision_codes_scd2`
    both live in `bronze_iso_publish`, both via
    `create_auto_cdc_from_snapshot_flow` against a
    `@dp.temporary_view()`/private `@dp.materialized_view()` that stamps
    `transformed_timestamp`, both excluding `ingested_timestamp`/
    `transformed_timestamp` via `track_history_except_column_list` — same
    reasoning as AirROI's pattern (NAMING.md's "Platform-added timestamp
    columns").
  - **`country_code_alpha2` is a clean SCD key** (249 distinct of 249
    rows, confirmed via the real source data), but
    **`subdivision_code` alone is not** — confirmed via a real pipeline
    failure, not assumed from the CSV's column names. 6,260 rows but only
    5,046 distinct `subdivision_code` values: a subdivision can carry more
    than one localized name (e.g. `AF-BDS` has separate Dari/`fa` and
    Pashto/`ps` names for the same Afghan province). Adding
    `language_code` alone still leaves 175 collisions (different
    transliterations of the same name in the same language). The real key
    is `(subdivision_code, language_code, subdivision_name)` — confirmed
    to fully partition the data with zero inconsistency in the remaining
    columns per group. Same category of finding as NSW Spatial's
    `addressstringoid`-vs-`propid` key correction.
  - **Even the corrected 3-column key isn't quite enough** — a real
    `create_auto_cdc_from_snapshot_flow` run hit
    `DUPLICATE_KEY_VIOLATION` on `RU-DA`/`ru`/`Dagestan`: 10 of 6,260 rows
    are genuine full-row duplicates in the source CSV itself (confirmed
    byte-identical, not a values conflict). Auto CDC's snapshot flow
    rejects more than one row per key outright, with zero tolerance for
    identical duplicates.
  - **Quarantine pattern, same shape as ACNC's**: rather than silently
    dropping the 10 duplicate rows inside the SCD pipeline,
    `subdivision_codes_deduped` (private, feeds Auto CDC) and
    `bronze_iso.subdivision_codes_quarantine` (public, in the raw schema)
    read the same `subdivision_codes_raw` with complementary logic — a
    `row_number()` window over the SCD key keeps rank 1 in the deduped
    path and rank > 1 in quarantine — so `raw = deduped_distinct_keys +
    quarantine` exactly, checked by `verify_iso_country_reference_scd.py`.

## Development style

- Notebook-first: logic lives in Databricks notebooks (stored as `.py` source files
  in the bundle). Shared utilities go in `src/` as importable Python modules.
- Formatter: `ruff` for all Python (notebooks and scripts).
- Package manager: `uv` (see global CLAUDE.md).

## Workflow

@CONTRIBUTING.md

Non-trivial changes go through OpenSpec first: propose (`openspec change new <name>`),
agree the spec, implement, archive. See `openspec/` and each change's `design.md` for
the decision record behind what's built.

## Operational notes

- **`tst`/`prd` should be deployed via CI/CD (GitHub Actions on merge to
  `main`), not a local human `bundle deploy -t tst|prd`** — once a resource in
  a target has ever been deployed by the CI/CD service principal, a later
  local deploy by a human identity fails on that resource with `403
  PERMISSION_DENIED: Only metastore admins can change pipeline owner`
  (confirmed via a real `tst` deploy attempt against the pre-existing
  `neon_ecommerce_ingestion` pipeline). A target with nothing deployed yet
  (e.g. `prd`, before its first deploy) won't hit this, since there's no
  existing owner to conflict with — but that's an accident of ordering, not a
  reason to keep deploying that target locally afterward.
  - **The reverse order breaks CI/CD's automated deploys, and is why this
    guardrail matters, not just a style preference.** `tst`/`prd` both set an
    explicit `root_path: /Workspace/Shared/.bundle/${bundle.name}/${bundle.target}`
    in `databricks.yml` (unlike `dev`, which has no override and defaults to
    a per-identity path) — meaning every identity that ever deploys to
    `tst`/`prd` writes to the *same* shared resources, by design, since
    exactly one real `tst`/`prd` copy should exist. Confirmed via a real,
    silent, multi-merge CI/CD breakage: a human `bundle deploy -t tst` at
    some point in the past left several `tst` jobs/pipelines owned by the
    human identity; every subsequent automated `deploy-tst` GitHub Actions
    run then failed trying to update those specific resources'
    `permissions:` blocks (`403 PERMISSION_DENIED: ... only workspace admins
    can change the owner of a job` / `Only admins can change pipeline
    owners`), even though most of the bundle's other resources deployed
    fine. The failure only surfaced clearly by diffing every job's/pipeline's
    `run_as_user_name` against the CI/CD SP's client ID
    (`databricks jobs get <id>` / `databricks pipelines get <id>`) — the
    GitHub Actions log only showed the first handful of 403s per run, not
    the full set. Fix: delete every human-owned `tst`/`prd` job/pipeline
    (safe — same "human-identity copies are disposable" reasoning as dev,
    just applied to `tst`/`prd` instead), then re-run the deploy so the SP
    recreates and owns them cleanly. `prd`'s manual-approval gate meant this
    had been silently queued to fail there too, never yet triggered — worth
    checking proactively (same ownership diff) before ever approving a
    `deploy-prd` run, not just reactively after it fails.
- **Free Edition's serverless compute pool is small and shared across
  pipelines/warehouses/jobs** — a pipeline run can fail with `RESOURCE_EXHAUSTED:
  You've hit the limit for serverless compute for free usage` even when
  nothing looks busy (`databricks clusters list` empty, all pipelines `IDLE`).
  Check `databricks warehouses list` for a `RUNNING` warehouse sitting idle and
  `databricks warehouses stop <id>` it before retrying — that resolved it in
  practice, confirmed via a real retry.
- **Run one pipeline/job at a time on Free Edition — never trigger two
  `bundle run` / `databricks pipelines start-update` / `databricks jobs
  run-now` calls concurrently**, including across unrelated pipelines. This
  is the direct consequence of the shared, capacity-limited serverless pool
  above: two concurrent runs compete for the same small pool and make
  `RESOURCE_EXHAUSTED` far more likely, not just a theoretical race. Treat
  each `bundle run` as blocking — wait for one to reach `COMPLETED`/`FAILED`
  before starting the next — even when a background shell makes it tempting
  to fire off several at once. This constraint is specific to Free Edition;
  `demo-databricks-iac`'s reserved `deployment/single_workspace/` and
  `deployment/multiple_workspaces/` placeholders (see its CLAUDE.md) are for
  a future paid tier that may lift it via classic clusters or a larger
  serverless budget — not yet verified, since neither is built.
- **The CI/CD SP's `[dev svc_cicd_github] ...`-prefixed pipeline/job copies
  are the canonical, durable dev data going forward — the
  `[dev handsonessential] ...` (or whichever human deploys locally) copies are
  disposable personal-iteration artifacts.** Confirmed the hard way: an
  earlier cleanup deleted the human-identity dev copy of
  `neon_ecommerce_ingestion`, which (per Databricks' default pipeline-delete
  behavior) dropped `bronze_neon.*_raw` along with it — the Neon Postgres
  source itself was untouched, but the ingested-into-Databricks copy had to be
  rebuilt from scratch. Never treat a human-identity dev pipeline/job's data
  as something worth preserving; if it needs deleting, delete it freely. To
  run something as the SP without local M2M credentials, just trigger the
  SP-owned resource's ID directly (`databricks pipelines start-update
  <pipeline_id>` / `databricks jobs run-now <job_id>`) — execution identity is
  a property of the resource, not the caller. See
  `demo-databricks-iac`'s CLAUDE.md ("CI/CD service principal pipeline
  execution") for the grants this needed to actually work.

## Guardrails — never do without explicit confirmation

- No classic clusters — serverless only
- No account-level API calls (Free Edition scope is workspace-level only)
- No `%run` — use proper imports from `src/`
- No `%pip install` in notebooks — declare dependencies in bundle config
- No hardcoded secrets or connection strings — always `dbutils.secrets.get()`
- No destructive DDL (`DROP TABLE`, `TRUNCATE`, `DELETE`) without explicit user approval
- No direct writes to `mdp_prd` catalog from ad-hoc notebooks
