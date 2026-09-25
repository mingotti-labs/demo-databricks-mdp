# Data Sources Registry

Authoritative inventory of every upstream system feeding Bronze, what Bronze
Publish exposes for each one, and what is currently consumed downstream.
Update this file whenever a source is onboarded to Bronze Publish, or when a
new layer starts (or stops) consuming an existing source.

## SCD selection rule

Where Bronze Publish exposes more than one SCD variant for the same entity,
downstream layers select in this order: **SCD2 > SCD1 > SCD0** (raw). Use the
richer variant if it exists; fall back only when it doesn't. See
[silver.md](../medallion/silver.md) for how Silver Landing applies this.

## Sources

### neon
- **What it is**: Neon Postgres e-commerce operational database
- **Ingestion pattern**: Lakeflow Connect, query-based (gateway-free)
- **Bronze raw**: `bronze_neon.{customers,products,orders,order_items}_raw`
- **Bronze Publish** (`bronze_neon_publish`):
  - customers: `customers_scd1`, `customers_scd2`, `customers_scd1_sql`
  - products: `products_scd1`, `products_scd2`, `products_scd1_sql`
  - orders: `orders_scd1`, `orders_scd1_sql`
  - order_items: `order_items_scd1`, `order_items_scd1_sql`
- **Consumed by Silver Landing**: yes — `customers_scd2`, `products_scd2`,
  `orders_scd1`, `order_items_scd1` (all Python variants) → `silver_landing_neon`

### clickstream
- **What it is**: Synthetic web clickstream events, file-drop via UC Volume
- **Ingestion pattern**: Auto Loader (Lakeflow Declarative Pipeline streaming
  table); several schema-evolution demo variants exist in `bronze_clickstream`
  (`fail_on_new_columns`, `none`, `rescue`, `add_new_columns`)
- **Bronze raw**: `bronze_clickstream.web_events_raw` (+ demo variants)
- **Bronze Publish** (`bronze_clickstream_publish`): `web_events_scd1`,
  `web_events_scd1_sql`
- **Consumed by Silver Landing**: yes — `web_events_scd1` (Python) →
  `silver_landing_clickstream`

### ungm
- **What it is**: UNGM UNSPSC classification, public REST API
- **Ingestion pattern**: custom Python/API fetch (`src/common/ungm.py`)
- **Bronze raw**: `bronze_ungm.unspsc_public_raw`
- **Bronze Publish** (`bronze_ungm_publish`): `unspsc_public_scd1`,
  `unspsc_public_scd2`
- **Consumed by Silver Landing**: yes — `unspsc_public_scd2` →
  `silver_landing_ungm`

### acnc
- **What it is**: ACNC Charity Register, data.gov.au CKAN Data API
- **Ingestion pattern**: reusable PySpark Custom Data Source connector
  (CKAN `datastore_search`)
- **Bronze raw**: `bronze_acnc.charity_register_raw` (+ `charity_register_quarantine`)
- **Bronze Publish** (`bronze_acnc_publish`): `charity_register_scd1`,
  `charity_register_scd2` (`charity_register_valid` is a private
  pipeline-scoped intermediate, not published)
- **Consumed by Silver Landing**: yes — `charity_register_scd2` →
  `silver_landing_acnc`

### nsw_spatial
- **What it is**: NSW "Land Parcel and Property Theme", Esri ArcGIS REST
  FeatureServer
- **Ingestion pattern**: reusable custom Spark data source connector
- **Bronze raw**: `bronze_nsw_spatial.property_raw`
- **Bronze Publish** (`bronze_nsw_spatial_publish`): `property_scd1`,
  `property_scd2`
- **Consumed by Silver Landing**: yes — `property_scd2` →
  `silver_landing_nsw_spatial`

### airroi
- **What it is**: AirROI short-term rental market intelligence API (4 real
  markets: Vitoria da Conquista/BA, Urubici/SC, Tauranga/NZ, Prado/BA)
- **Ingestion pattern**: custom connector
- **Bronze raw**: `bronze_airroi.{market_metrics_all,market_summary}_raw`
- **Bronze Publish** (`bronze_airroi_publish`): `market_metrics_all_scd2`,
  `market_summary_scd2` (no SCD1 variant exists for either)
- **Consumed by Silver Landing**: yes — both → `silver_landing_airroi`

### iso
- **What it is**: ISO 3166-1/3166-2 country and subdivision reference data,
  public GitHub CSV mirror (CC BY-SA 4.0)
- **Ingestion pattern**: small fetch helper (`src/common/iso3166.py`),
  static CSV, no connector needed
- **Bronze raw**: `bronze_iso.{country_codes,subdivision_codes}_raw`
  (+ `subdivision_codes_quarantine`)
- **Bronze Publish** (`bronze_iso_publish`): `country_codes_scd2`,
  `subdivision_codes_scd2` (no SCD1 variant for either;
  `subdivision_codes_deduped` is a private pipeline-scoped intermediate,
  not published)
- **Consumed by Silver Landing**: not yet — onboarded after
  `phase4a-silver-landing`
