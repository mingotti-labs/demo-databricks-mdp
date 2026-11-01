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
  config.json             # edition (free|standard) and its environments
  databricks.yml          # GENERATED from cicd/databricks/<edition>.yml -- do not edit
  resources/
    jobs/
    pipelines/
    dashboards/
    apps/
  src/
    layers/
      bronze/
        neon/
        atlas/
        clickstream/
          python_add_new_columns/   # canonical; the other 7 variants live in references/patterns/
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
        geonames/           # country_info_raw.py, admin1_codes_raw.py,
                            # admin2_codes_raw.py, cities_raw.py -- src/common/geonames.py
                            # fetch helpers (plain + zip dump), no connector needed
        geonames_publish/   # {country_info,admin1_codes,admin2_codes,cities}_scd2.py --
                            # SCD2 only, no SCD1; all four keys confirmed unique against
                            # real data, no quarantine table needed
      silver/
        domain/
          investments/   # silver_domain_investments: nine materialized views
                         # (entities.py, market_data.py, company_fundamentals.py)
      gold/
        analytics_gateway/
        integration_gateway/
        ai_gateway/
    common/               # shared importable Python modules -- NOT wheel-packaged (no
                          # build-system config yet); see the UNGM "Sources" entry below
                          # for the confirmed sys.path-based import mechanism pipelines use
    seed_data/            # one-off synthetic-data generators, not part of any medallion layer
  data/
    portfolio/            # curated settings CSVs (master copy), copied to a volume by run_portfolio
  tests/
    common/               # mirrors src/common/ only — NOT src/layers/
    cicd/                 # unit tests for cicd/ (offline, no Databricks)
  cicd/                   # CI/CD tooling, not deployed: affected_units.py picks the run_<unit> jobs a merge affects
  verification/           # live-environment functional checks — see "Verification vs validation"
  references/
    docs/                 # all documentation; registers/design-patterns.md lists every implemented design pattern
    patterns/             # separate dev-only bundle (own databricks.yml) for pattern-only implementations; the main bundle excludes references/** from sync
```

- `resources/<type>/`: grouped by resource kind (job/pipeline/dashboard/app), not one flat directory.
- `src/layers/{bronze,silver,gold}/<source-or-domain-or-gateway>/`: mirrors the catalog/schema naming below, not the ingestion pattern or use case. Exception: the schema-evolution-mode variants have one subfolder each, isolating each pipeline's `libraries` glob so pipelines never pick up a sibling variant's source file (see `phase3b-clickstream-schema-evolution-variants`'s design.md). Only `bronze/clickstream/python_add_new_columns/` is ever actually run; the other 7 are documented, deployable reference material in the separate patterns bundle, `references/patterns/src/bronze/autoloader_<mode>_<language>.{py,sql}`.
- `src/common/`: the only part of `src/` that is plainly importable, wheel-packaged Python.
- `src/seed_data/`: synthetic-data generation notebooks — not a medallion layer, not deployed data, just a way to populate a source system for demo/dev purposes. Two shapes so far: truncate-and-reseed for a database source (`seed_neon_ecommerce.py`) vs. append-a-new-batch for a file-drop source (`generate_clickstream_events.py`) — pick the shape that matches how the real source would behave, not one convention for both.
- `tests/` mirrors `src/common/` 1:1 (standard `databricks bundle init` convention). It does not mirror `src/layers/` — pipeline transformation correctness is validated with inline data-quality expectations and `bundle run --refresh`, not pytest.
- `cicd/`: CI-only scripts (never uploaded with the bundle, unlike `src/`). `affected_units.py` decides which `run_<unit>` jobs `main.yml` runs after a `tst`/`prd` deploy — see CONTRIBUTING.md's "Adding a runnable unit".
- `verification/`: Databricks notebooks that check a *deployed* feature actually works against real/synthetic data (connection liveness, row-count parity, referential integrity), chained into a job per pattern. See CONTRIBUTING.md's "Verification vs validation" section — deliberately distinct from `tests/`.

### Resource type ownership: this repo vs. Terraform

The Databricks Asset Bundle resource schema (`databricks bundle schema`, CLI v1.16.1) defines 35 resource types. Not all of them belong in this repo's `resources/`. Split by who owns them:

**Terraform (`demo-databricks-iac`) owns** — Unity Catalog governance and source-DB infra, same family as what Phase 1 already provisions:
`catalogs`, `schemas`, `external_locations`, `secret_scopes`, `secrets`, `volumes`, and (if Lakebase is adopted later) `database_catalogs`, `database_instances`, `postgres_projects`, `postgres_branches`, `postgres_endpoints`, `postgres_databases`, `postgres_roles`, `postgres_snapshot_schedules`, `postgres_catalogs`.

**Not applicable** — Free Edition is serverless-only (see Guardrails below): `clusters`, `cluster_policies`, `instance_pools`.

**This repo (`demo-databricks-mdp`) owns** — workload resources, added under `resources/<type>/` only when a phase actually needs that type (do not pre-scaffold empty folders):
`jobs`, `job_runs`, `pipelines`, `dashboards`, `apps`, `alerts`, `experiments`, `models`, `registered_models`, `model_serving_endpoints`, `quality_monitors`, `genie_spaces`, `vector_search_endpoints`, `vector_search_indexes`, `sql_warehouses`, `postgres_synced_tables`, `synced_database_tables`.

## DAB targets

Targets come from `config.json`'s edition (`cicd/databricks/<edition>.yml`),
all pointing to the same workspace, differentiated by catalog:

- `dev` → `mdp_dev`
- `tst` → `mdp_tst` (standard edition only)
- `prd` → `mdp_prd`

The committed edition is `free` (dev and prd only): a metastore is capped at
500 tables and each environment multiplies every table. The root
`databricks.yml` and `.github/workflows/` are generated; see CONTRIBUTING.md.

## Sources

- **One pipeline per layer** (openspec `pipeline-per-layer`): acnc, ungm, iso,
  geonames, nsw_spatial, airroi and clickstream each have `bronze--<source>--<target>` (the
  ingestion pipeline also builds `bronze_<source>_publish.*` by qualified name;
  every SCD2 table has `pipelines.reset.allowed=false`, so a full refresh of
  the bronze pipeline is refused, by design) and `silver--<source>--<target>`.
  ungm/iso/geonames/nsw_spatial moved in `ungm-iso-geonames-nsw-two-pipelines`
  (their `run_<source>` jobs exist; their dev tables were recreated under the
  CI/CD service principal rather than migrated). airroi, clickstream and neon
  moved in `refactor-airroi-clickstream-neon`; see the spec for the exceptions.
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
  - The Bronze Publish and Silver Landing tables were removed in
    `neon-publish-cleanup` (2026-11, 18 table slots); only `bronze_neon` and its
    pipeline remain. `bronze_neon.*_raw` is upsert-maintained (Lakeflow Connect
    MERGEs changed rows via `cursor_columns`), which is what shaped the removed
    SCD code. The findings live with the pattern
    `bronze_publish_scd2_autocdc_snapshot_python` in `references/patterns/`:
    streaming Auto CDC fails against an upserted source
    (`DELTA_SOURCE_TABLE_IGNORE_CHANGES`), `skipChangeCommits` silently drops
    updated rows, and switching a snapshot flow's `source` after it has run can
    add duplicate no-op versions. The removed code and `RECOVERY.md` are in
    `references/backups/neon/`.
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
    re-verified here. Those 7 live in the separate dev-only patterns bundle
    (`references/patterns/`, change `references-patterns-bundle`) and are
    displayed with the source system `pattern`
    (`bronze--pattern--autoloader--<language>--<mode>--<target>`), since they
    are reference material, not part of clickstream's flow; the canonical
    pipeline and both SCD pipelines (the Python one feeds Silver Landing)
    keep `clickstream`. They write to the dev-only `pattern_bronze` schema (iac repo), are not deployed to `tst`/`prd` and hold no
    tables. See `src/layers/bronze/clickstream/` and
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
    `unspsc_public_raw.py`'s header. **Never list `src/common/**` in a
    pipeline's `libraries`**: it adds nothing to imports, but makes every
    `common/` file run as pipeline source, so a `common/` module importing a
    sibling (`from common import ...`) fails that pipeline at initialisation
    — confirmed when it broke `silver_landing_airroi` in `dev` during
    `phase4d-silver-normalised-framework`. Twelve pipelines carried the
    leftover glob until it was removed.
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
    `tst` pulls 500 rows; `prd` pulls the full dataset (~66k rows,
    confirmed via the CKAN API before this was built). **`dev` also pulls
    the full dataset since `phase4e-silver-normalised-acnc`** — the
    500-row sample hid real data-quality conflicts (Postcode → State: 0
    violations sampled, 157 at full scale) from Silver Normalised
    profiling; free CKAN API, no cost to pulling the full set.
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
  - **`ingested_timestamp` retrofitted** (`phase4e-silver-normalised-acnc`,
    folded into that change rather than its own, per NAMING.md): stamped
    in `charity_register_raw`; `transformed_timestamp` stamped directly in
    `charity_register_valid` (already a real filtering view, so no extra
    wrapper dataset needed, unlike AirROI's `market_summary_transformed`);
    both excluded from `charity_register_scd2`'s history tracking.
    Confirmed via a real `dev` run: no full refresh of the existing SCD2
    target — its 10 pre-existing closed versions survived intact, now with
    a null `ingested_timestamp` (Auto CDC doesn't rewrite closed versions;
    accepted, downstream `max()` aggregation ignores nulls).
  - **One pipeline per layer** (`acnc-two-pipelines`, 2026-10): the bronze
    pipeline `acnc_charity_register_ingestion` (`bronze--acnc--<target>`)
    builds `bronze_acnc.*` and, by qualified name, `bronze_acnc_publish.*`;
    the silver pipeline `silver_normalised_acnc` (`silver--acnc--<target>`)
    builds Silver Normalised and, by qualified name,
    `silver_landing.acnc__charity_register`. The SCD and Landing pipelines
    were removed after their tables were moved (SCD2 history intact in all
    three environments). `charity_register_scd2` has
    `pipelines.reset.allowed=false`: a full refresh of the bronze pipeline
    is refused with a `DLTAnalysisException` (by design; outside
    development mode Databricks auto-retries the failed update a few
    times). Refresh a single upstream table selectively if ever needed.
  - **Corrected platform timestamps** (`correct-platform-timestamps`,
    2026-10): `charity_register_scd2` is the bronze full pattern: snapshot Auto CDC
    in the bronze pipeline from a view over `charity_register_valid` without
    `ingested_timestamp` (versions are the update's time, `__START_AT`);
    Silver Landing reads its change feed and settles both timestamps; Silver
    Normalised is rebuilt by the `normalised` task. See NAMING.md
    "Platform-added timestamp columns".
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
    quarantine` exactly, checked by `verification/verify_bronze.py` (spec: `verification/bronze_checks/iso.yml`).
  - **ISO 10383 market identifier codes** (`iso-mic`, 2026-10): the same source
    carries `market_identifier_codes` (2,889 rows: 1,596 operating markets, 1,293
    segments), a full-load Materialized View from `iso10383_mic_url`, SCD2 by
    `market_identifier_code`, Landing `silver_landing.iso__market_identifier_codes`
    with the four date columns as DATE. `src/common/iso10383.py` decodes the bytes
    as UTF-8 (`requests` would guess ISO-8859-1) and fails when a source column is
    renamed. The ISO terms allow free use but not reproducing the whole list for
    third parties; the raw table's comment says so. Read by the Silver Domain
    `market` table (`silver-domain-investments`).
- **GeoNames country/admin1/admin2/city gazetteer data** (Phase 3j) — the
  city/locality half of the reference-data backbone under ISO 3166's
  country/state half. Four static files from a public, unauthenticated
  `download.geonames.org` mirror (CC BY 4.0): `countryInfo.txt` (252
  rows), `admin1CodesASCII.txt` (3,865 rows), `admin2Codes.txt` (47,643
  rows), and `cities500.zip` (235,878 rows — all populated places with
  population > 500, the smallest of GeoNames' official variants).
  `src/common/geonames.py` has two helpers: `fetch_geonames_dump` (plain
  tab-delimited) and `fetch_geonames_zip_dump` (zip-wrapped). Neither ISO
  file format gave DictReader a usable header row — three files have no
  header at all, and `countryInfo.txt`'s real header is buried among
  `#`-prefixed documentation lines, not reliably first or last — so both
  helpers take `fieldnames` explicitly rather than trying to parse one out.
  `cities500.zip` at ~14MB compressed is an order of magnitude larger than
  UNGM's ~1.4MB fetch but still a single driver-side fetch, same reasoning
  as UNGM's.
  - **All four SCD keys (`iso_alpha2`, `code` for both admin tables,
    `geonameid`) were confirmed unique against the real fetched data before
    any pipeline code was written** — the proactive check ISO's
    `subdivision_code` surprise motivated. All four held up; no quarantine
    table exists for any GeoNames table.
  - Same shape as ISO's otherwise: `ingested_timestamp` on each `_raw`
    table, `transformed_timestamp` stamped at the SCD2 layer via a
    `@dp.temporary_view()` per table, both excluded via
    `track_history_except_column_list`, SCD2-only (no SCD1), CC BY 4.0
    attribution as a Unity Catalog table comment on all four `_raw` tables.
- **Wikipedia S&P 500 list** (`wikipedia-sp500-ingestion`, dividend portfolio
  story) -- first source of the story: the `constituents` table of "List of S&P
  500 companies", parsed with lxml by `src/common/wikipedia_sp500.py` (fails on a
  layout change). `bronze_wikipedia.sp500_constituents_raw` (Materialized View,
  text values as the page shows them, symbols with dots), SCD2
  `bronze_wikipedia_publish.sp500_constituents_scd2` keyed by `symbol` and
  `silver_landing.wikipedia__sp500_constituents`. SCD2 versions are the index
  membership history (an exit closes a version), kept from the first load. One
  weekly run job `run_wikipedia`; no Silver Normalised. The dividend story chose
  Wikipedia because FMP's free plan refuses the list (probes in
  `references/docs/registers/probes.md`). Wikipedia needs a contact User-Agent:
  the `http_user_agent` bundle variable, reused by the SEC source.
- **Portfolio internal data** (`portfolio-internal-settings`, dividend portfolio
  story) -- company-owned data, not an upstream system: six curated CSVs
  committed in `data/portfolio/` (SEC concept mapping, predecessor CIKs,
  settings, risk levels, target mix, benchmarks), copied by `run_portfolio`'s first task
  (`src/common/copy_repo_files.py`) into `bronze_portfolio.s3_raw/<name>/landing/`
  on every run, so the repo is the master. `bronze_portfolio.<name>_raw` text
  Materialized Views, SCD2 in `bronze_portfolio_publish` (the history of every
  setting) and `silver_landing.portfolio__<name>`. The copy task's `source_glob` is also
  how CI selects the unit when a CSV changes. Real purchases (later) are never
  committed and never overwritten by the copy.
- **SEC EDGAR** (`sec-company-facts`, dividend portfolio story) -- the first
  source with **append-only, replayable raw** (user, 2026-10-28): `run_sec`'s
  first task (`src/common/fetch_sec.py`) calls SEC for the current Wikipedia
  CIKs plus the `portfolio` predecessor CIKs, keeps the mapped concepts in long
  form and writes dated JSON Lines into `bronze_sec.s3_raw`, only for companies
  whose facts changed; Auto Loader appends them into `bronze_sec.*_raw`
  streaming tables. `ingested_timestamp` is the fetch time written by the task.
  SCD2 in `bronze_sec_publish` is built from each company's latest file; bronze
  verification compares that latest file (`compare_latest_file_per`).
  Verification is a dev tool: CI runs units with `verify=false`, prd relies on
  the warn expectations. Yahoo follows this pattern; Wikipedia and portfolio
  move to it afterwards.
- **Yahoo Finance** (`yahoo-market-data`, dividend portfolio story) -- prices,
  dividends and splits (`events`), next pay dates (`calendar`) and options
  activity via `yfinance` (unofficial), for every symbol ever in the Wikipedia
  S&P 500 history plus the `portfolio` benchmarks. `run_yahoo`'s first task
  (`src/common/fetch_yahoo.py`, the only notebook allowed `%pip`) is
  incremental: prices from the last stored day minus one; a symbol is reloaded
  in full when it is new, has a dividend or split in the new days (Yahoo
  restates every earlier adjusted close, and every price and dividend on a
  split), or is named in the `reload_symbols` job parameter. It works in
  batches of 50 and records progress per symbol in `bronze_yahoo.fetch_state`,
  so a repaired run skips the symbols it already fetched; it fails at the end
  if more than 2% of current members have no prices. Append-only raw as SEC;
  Bronze Publish by streaming Auto CDC (`prices_scd1`, `events_scd1`,
  `options_scd1`, `calendar_scd2`). Yahoo's option open interest is 0
  everywhere, so options volume is kept too.
- **RBA** (`rba-rates`, dividend portfolio story) -- exchange rates (F11.1),
  money market rates with the cash rate target (F1), government bond yields (F2)
  and indicator lending rates incl. mortgages (F5), free CSV files from
  `rba_tables_url` (the folder returns 403; the files are fine). All four share
  one long table (one row per `series_id` and `observation_date`, told apart by
  `table_id`) to save table-quota slots. `run_rba`'s first task
  (`src/common/fetch_rba.py`) downloads and parses every file before writing any;
  after the first run it writes only the 31 days before each table's last stored
  date (late-filled cells, revisions); `reload=true` writes everything. Append-only
  raw as SEC; Bronze Publish `observations_scd1`; Landing `silver_landing.rba__observations`
  with `observation_date` and `publication_date` converted to dates.
- **FRED** (`fred-rates`, dividend portfolio story) -- the US 10-year Treasury
  yield (`DGS10`, a market yield) and the Fed's policy rate (`DFF` effective,
  `DFEDTARU` / `DFEDTARL` target range, the counterpart of the RBA cash rate
  target), from the FRED API with the key in secret scope `fred`. One long table
  as RBA. `run_fred`'s first task (`src/common/fetch_fred.py`) requests only the
  31 days before each series' last stored date (`reload=true` for everything),
  skips the `.` (no value) days, and writes one dated file. The key is in the
  query string, so all requests go through `get_json`, which re-raises failures
  without the URL. Landing `silver_landing.fred__observations` has
  `observation_date` as a date.
- **Silver Domain investments** (`silver-domain-investments`, dividend portfolio
  story) -- schema `silver_domain_investments`, one serverless pipeline of nine
  materialized views reading `silver_landing` only: `company` (SEC central index
  key), `market` (ISO operating markets), `listing` (a trading symbol on a market;
  market from Yahoo's `exchange_code`), `index_membership`, `price_daily`,
  `dividend` (A$ amount, pay date, `is_special`), `company_fundamentals` (a row
  per 10-K or 10-Q filing, point in time: `valid_from_date` is the filing date;
  trailing twelve months and balance sheet figures from SEC facts),
  `market_rate_daily` (six rates) and `options_activity`. Ids are hashes:
  `company_id = sha2('sec:' + central_index_key)`, `listing_id = sha2(market:
  symbol)`; surrogate keys belong in gold. Join: `price_daily.listing_id =
  listing.listing_id`, `listing.company_id = company.company_id`. Shared logic in
  `src/common/investments.py` (figure list, rates, exchange mapping, SQL
  snippets). `run_investments` runs the pipeline and, with `verify=true`,
  `verification/verify_silver_domain_investments.py` (CI runs it with
  `verify=false`; the `check_symbol` parameter adds a deliberate-failure check).
  Run the source units first. Findings: `CXI` (the VIX benchmark) maps to `XCBO`;
  `is_special` flags step changes as well as one-offs.
- **Landing checks per source**: `verification/silver_landing_checks/<source>.yml`
  lists a source's Landing tables for `verify_silver_landing`; a new source adds
  one file (a test fails if a source with a Landing schema has none) and no
  shared notebook, so CI runs only that source.

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
- **Free Edition quotas: 500 tables per metastore, 50 schemas per catalog.**
  Read them with `databricks resource-quotas get-quota metastore <metastore_id>
  table-quota` and `get-quota catalog <catalog> schema-quota`; both counts
  refresh with a lag of minutes, so a create right after a drop can still fail
  on the old count. Every streaming table and materialized view costs 2 table
  slots (a hidden `__materialization_mat_<pipeline>_<table>_1` twin), a plain
  Delta table 1, and a pipeline with a Unity Catalog event log 1 more.
  Dropping a pipeline table, or deleting its pipeline, leaves the twin behind:
  drop it too, or the slot stays used. Budget the slots of every new source in
  its proposal (dev and prd). Silver Landing has one schema, `silver_landing`,
  for every source (`single-silver-landing-schema`) to stay under the schema
  quota.
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
  hold the dev data; a `[dev handsonessential] ...` copy (from a local
  deploy, now refused by the hook) must not own tables.** Run anything as the
  SP by triggering the SP-owned resource's id (`cicd/run_dev.py`, `databricks
  jobs run-now <job_id>`, `databricks pipelines start-update <pipeline_id>`):
  execution identity is a property of the resource, not the caller. See
  `demo-databricks-iac`'s CLAUDE.md ("CI/CD service principal pipeline
  execution") for the grants this needed.
  - **A human copy's tables cannot move to the SP without a reload**
    (`dev-runs-as-service-principal`, probes O1-O8 in
    `references/poc/pipeline-ownership/`): the move checks the owner of the
    source pipeline, even after it is deleted, and of the destination; a
    pipeline's owner cannot change on Free Edition (`Only metastore admins can
    change pipeline owner`), and the human cannot act as the SP. Procedure:
    the user deletes the human pipeline (a regular pipeline's tables stay),
    the tables are dropped with approval, the SP's pipelines rebuild them.
    Append-only raw (SEC, Yahoo) replays every file from the volume, SCD2
    history included; a full-load source's dev SCD2 history restarts. A plain
    table (`fetch_state`) is handed over with `ALTER TABLE ... OWNER TO`; a
    pipeline table cannot be (its owner follows the pipeline's run-as).
  - An earlier note said deleting the human `neon_ecommerce_ingestion` copy
    dropped `bronze_neon.*_raw`; that was a Lakeflow Connect ingestion
    pipeline. Regular pipelines kept their tables in every test since.
  - Human copies that still owned dev tables were `bronze--neon--scd--python`,
    `bronze--neon--scd--sql`, `silver--landing--neon` and
    `silver--landing--clickstream` (15 tables, 2026-10-21); the neon ones are
    gone with `neon-publish-cleanup`.

## Guardrails — never do without explicit confirmation

- No classic clusters — serverless only
- No account-level API calls (Free Edition scope is workspace-level only)
- No `%run` — use proper imports from `src/`
- No `%pip install` in notebooks — declare dependencies in bundle config. One exception (user, 2026-10-29): `src/common/fetch_yahoo.py` installs its pinned `yfinance`, since a notebook task cannot declare a library
- No hardcoded secrets or connection strings — always `dbutils.secrets.get()`
- No destructive DDL (`DROP TABLE`, `TRUNCATE`, `DELETE`) without explicit user approval
- No direct writes to `mdp_prd` catalog from ad-hoc notebooks
- No local `databricks bundle deploy|run|destroy` of the main bundle, in any target — dev runs go through the PR's `deploy-dev` and `cicd/run_dev.py` (CONTRIBUTING step 4); a `PreToolUse` hook (`cicd/block_bundle_deploy.py`) refuses it. The patterns bundle (`references/patterns/`) is the exception
