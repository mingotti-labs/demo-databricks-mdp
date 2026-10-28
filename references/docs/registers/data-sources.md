# Data Sources Registry

Authoritative inventory of every upstream system feeding Bronze, what Bronze
Publish exposes for each one, and what is currently consumed downstream.
Update this file whenever a source is onboarded to Bronze Publish, or when a
new layer starts (or stops) consuming an existing source. Each source links to
the design patterns it uses, defined in [design-patterns.md](design-patterns.md).

## SCD selection rule

Where Bronze Publish exposes more than one SCD variant for the same entity,
downstream layers select in this order: **SCD2 > SCD1 > SCD0** (raw). Use the
richer variant if it exists; fall back only when it doesn't. See
[silver.md](../medallion/silver.md) for how Silver Landing applies this.

## Sources

### neon
- **What it is**: Neon Postgres e-commerce operational database
- **Design patterns**: [`bronze_lakeflow_query`](design-patterns.md#bronze_lakeflow_query), [`bronze_publish_scd2_autocdc_snapshot_python`](design-patterns.md#bronze_publish_scd2_autocdc_snapshot_python), [`bronze_publish_scd1_autocdc_snapshot_python`](design-patterns.md#bronze_publish_scd1_autocdc_snapshot_python), [`bronze_publish_scd1_materialized_view_sql`](design-patterns.md#bronze_publish_scd1_materialized_view_sql), [`bronze_publish_scd2_merge_sql`](design-patterns.md#bronze_publish_scd2_merge_sql), [`silver_landing_materialized_view_python`](design-patterns.md#silver_landing_materialized_view_python)
- **Bronze raw**: `bronze_neon.{customers,products,orders,order_items}_raw`
- **Bronze Publish** (`bronze_neon_publish`):
  - customers: `customers_scd2`
  - products: `products_scd2`
  - orders: `orders_scd1`
  - order_items: `order_items_scd1`
  - the SCD1 tables of customers and products and the SQL twins moved to the
    patterns bundle
- **Consumed by Silver Landing**: yes — `customers_scd2`, `products_scd2`,
  `orders_scd1`, `order_items_scd1` (all Python variants) → `silver_landing_neon`

### clickstream
- **What it is**: Synthetic web clickstream events, file-drop via UC Volume
- **Design patterns**: [`bronze_autoloader_add_new_columns_python`](design-patterns.md#bronze_autoloader_add_new_columns_python), [`bronze_publish_scd1_autocdc_stream_python`](design-patterns.md#bronze_publish_scd1_autocdc_stream_python), [`bronze_publish_scd1_autocdc_stream_sql`](design-patterns.md#bronze_publish_scd1_autocdc_stream_sql), [`silver_landing_materialized_view_python`](design-patterns.md#silver_landing_materialized_view_python)
- **Bronze raw**: `bronze_clickstream.web_events_raw` (+ demo variants)
- **Bronze Publish** (`bronze_clickstream_publish`): `web_events_scd1` (the SQL twin
  moved to the patterns bundle)
- **Consumed by Silver Landing**: yes — `web_events_scd1` (Python) →
  `silver_landing_clickstream`

### ungm
- **What it is**: UNGM UNSPSC classification, public REST API
- **Design patterns**: [`bronze_rest_api_materialized_view_python`](design-patterns.md#bronze_rest_api_materialized_view_python), [`bronze_publish_scd2_autocdc_full_load_python`](design-patterns.md#bronze_publish_scd2_autocdc_full_load_python), [`bronze_publish_scd1_autocdc_snapshot_python`](design-patterns.md#bronze_publish_scd1_autocdc_snapshot_python), [`silver_landing_change_feed_python`](design-patterns.md#silver_landing_change_feed_python), [`bronze_silver_pipeline_per_layer`](design-patterns.md#bronze_silver_pipeline_per_layer)
- **Bronze raw**: `bronze_ungm.unspsc_public_raw`
- **Bronze Publish** (`bronze_ungm_publish`): `unspsc_public_scd2`
- **Consumed by Silver Landing**: yes — `unspsc_public_scd2` →
  `silver_landing_ungm`

### acnc
- **What it is**: ACNC Charity Register, data.gov.au CKAN Data API
- **Design patterns**: [`bronze_custom_ckan_python`](design-patterns.md#bronze_custom_ckan_python), [`bronze_quarantine_null_key_python`](design-patterns.md#bronze_quarantine_null_key_python), [`bronze_publish_scd2_autocdc_full_load_python`](design-patterns.md#bronze_publish_scd2_autocdc_full_load_python), [`bronze_publish_scd1_autocdc_snapshot_python`](design-patterns.md#bronze_publish_scd1_autocdc_snapshot_python), [`silver_landing_change_feed_python`](design-patterns.md#silver_landing_change_feed_python), [`silver_normalised_spec_driven_python`](design-patterns.md#silver_normalised_spec_driven_python), [`bronze_silver_pipeline_per_layer`](design-patterns.md#bronze_silver_pipeline_per_layer)
- **Bronze raw**: `bronze_acnc.charity_register_raw` (+ `charity_register_quarantine`)
- **Bronze Publish** (`bronze_acnc_publish`): `charity_register_scd2` (`charity_register_valid` is a private
  pipeline-scoped intermediate, not published)
- **Consumed by Silver Landing**: yes — `charity_register_scd2` →
  `silver_landing_acnc`
- **Consumed by Silver Normalised**: yes — `silver_normalised_acnc` (spec
  `src/layers/silver/normalised/specs/acnc.yml`; base `charity_register`,
  4 bridges, 10 extracted entities, no address hierarchy)

### nsw_spatial
- **What it is**: NSW "Land Parcel and Property Theme", Esri ArcGIS REST
  FeatureServer
- **Design patterns**: [`bronze_custom_arcgis_python`](design-patterns.md#bronze_custom_arcgis_python), [`bronze_publish_scd2_autocdc_full_load_python`](design-patterns.md#bronze_publish_scd2_autocdc_full_load_python), [`bronze_publish_scd1_autocdc_snapshot_python`](design-patterns.md#bronze_publish_scd1_autocdc_snapshot_python), [`silver_landing_change_feed_python`](design-patterns.md#silver_landing_change_feed_python), [`bronze_silver_pipeline_per_layer`](design-patterns.md#bronze_silver_pipeline_per_layer)
- **Bronze raw**: `bronze_nsw_spatial.property_raw`
- **Bronze Publish** (`bronze_nsw_spatial_publish`): `property_scd2`
- **Consumed by Silver Landing**: yes — `property_scd2` →
  `silver_landing_nsw_spatial`

### airroi
- **What it is**: AirROI short-term rental market intelligence API (4 real
  markets: Vitoria da Conquista/BA, Urubici/SC, Tauranga/NZ, Prado/BA)
- **Design patterns**: [`bronze_rest_api_materialized_view_python`](design-patterns.md#bronze_rest_api_materialized_view_python), [`bronze_publish_scd2_autocdc_full_load_python`](design-patterns.md#bronze_publish_scd2_autocdc_full_load_python), [`silver_landing_change_feed_python`](design-patterns.md#silver_landing_change_feed_python), [`silver_normalised_spec_driven_python`](design-patterns.md#silver_normalised_spec_driven_python)
- **Bronze raw**: `bronze_airroi.{market_metrics_all,market_summary}_raw`
- **Bronze Publish** (`bronze_airroi_publish`): `market_metrics_all_scd2`,
  `market_summary_scd2` (no SCD1 variant exists for either)
- **Consumed by Silver Landing**: yes — both → `silver_landing_airroi`
- **Consumed by Silver Normalised**: yes — `silver_normalised_airroi` (spec
  `src/layers/silver/normalised/specs/airroi.yml`), rebuilt by the `normalised`
  task of `run_airroi`

### iso
- **What it is**: ISO 3166-1/3166-2 country and subdivision reference data,
  public GitHub CSV mirror (CC BY-SA 4.0)
- **Design patterns**: [`bronze_file_materialized_view_python`](design-patterns.md#bronze_file_materialized_view_python), [`bronze_quarantine_duplicate_key_python`](design-patterns.md#bronze_quarantine_duplicate_key_python), [`bronze_publish_scd2_autocdc_full_load_python`](design-patterns.md#bronze_publish_scd2_autocdc_full_load_python), [`silver_landing_change_feed_python`](design-patterns.md#silver_landing_change_feed_python), [`bronze_silver_pipeline_per_layer`](design-patterns.md#bronze_silver_pipeline_per_layer)
- **Bronze raw**: `bronze_iso.{country_codes,subdivision_codes}_raw`
  (+ `subdivision_codes_quarantine`)
- **Bronze Publish** (`bronze_iso_publish`): `country_codes_scd2`,
  `subdivision_codes_scd2` (no SCD1 variant for either;
  `subdivision_codes_deduped` is a private pipeline-scoped intermediate,
  not published)
- **Consumed by Silver Landing**: yes — `country_codes_scd2`/
  `subdivision_codes_scd2` → `silver_landing_iso` (`country_codes`,
  `subdivision_codes`)

### geonames
- **What it is**: GeoNames country/admin1/admin2/city gazetteer data,
  public dump-file mirror (CC BY 4.0)
- **Design patterns**: [`bronze_file_materialized_view_python`](design-patterns.md#bronze_file_materialized_view_python), [`bronze_publish_scd2_autocdc_full_load_python`](design-patterns.md#bronze_publish_scd2_autocdc_full_load_python), [`silver_landing_change_feed_python`](design-patterns.md#silver_landing_change_feed_python), [`bronze_silver_pipeline_per_layer`](design-patterns.md#bronze_silver_pipeline_per_layer)
- **Bronze raw**: `bronze_geonames.{country_info,admin1_codes,admin2_codes,cities}_raw`
- **Bronze Publish** (`bronze_geonames_publish`):
  `{country_info,admin1_codes,admin2_codes,cities}_scd2` (no SCD1 variant
  for any table; all four keys confirmed unique, no quarantine needed)
- **Consumed by Silver Landing**: yes — all four `_scd2` objects →
  `silver_landing_geonames` (`country_info`, `admin1_codes`,
  `admin2_codes`, `cities`)

### wikipedia
- **What it is**: the S&P 500 constituents table of Wikipedia's "List of S&P 500
  companies" (CC BY-SA 4.0), the index list of the dividend portfolio story
- **Design patterns**: [`bronze_file_materialized_view_python`](design-patterns.md#bronze_file_materialized_view_python), [`bronze_publish_scd2_autocdc_full_load_python`](design-patterns.md#bronze_publish_scd2_autocdc_full_load_python), [`silver_landing_change_feed_python`](design-patterns.md#silver_landing_change_feed_python), [`bronze_silver_pipeline_per_layer`](design-patterns.md#bronze_silver_pipeline_per_layer)
- **Bronze raw**: `bronze_wikipedia.sp500_constituents_raw`
- **Bronze Publish** (`bronze_wikipedia_publish`): `sp500_constituents_scd2`
  keyed by `symbol`; its versions are the index membership history
- **Consumed by Silver Landing**: yes, `silver_landing_wikipedia.sp500_constituents`

### portfolio
- **What it is**: company-owned data of the dividend portfolio story: curated
  settings committed in `data/portfolio/` (concept mapping, predecessor CIKs,
  settings, risk levels, target mix); the purchases CSV joins later
- **Design patterns**: [`bronze_volume_csv_materialized_view_python`](design-patterns.md#bronze_volume_csv_materialized_view_python), [`bronze_publish_scd2_autocdc_full_load_python`](design-patterns.md#bronze_publish_scd2_autocdc_full_load_python), [`silver_landing_change_feed_python`](design-patterns.md#silver_landing_change_feed_python), [`bronze_silver_pipeline_per_layer`](design-patterns.md#bronze_silver_pipeline_per_layer)
- **Bronze raw**: `bronze_portfolio.{concept_mapping,predecessor_ciks,settings,risk_levels,target_mix}_raw`
- **Bronze Publish** (`bronze_portfolio_publish`): the same five as `_scd2`
- **Consumed by Silver Landing**: yes, `silver_landing_portfolio` (five tables)
