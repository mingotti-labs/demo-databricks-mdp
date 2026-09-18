# Naming conventions — demo-databricks-mdp

## Catalog & schema structure

Catalogs: `mdp_dev`, `mdp_tst`, `mdp_prd`

| Layer | Schema pattern | Purpose |
|---|---|---|
| Bronze | `bronze_<source>` | Raw ingestion, append-only |
| Bronze history | `bronze_<source>_history` | Full change history, CDC replay safety net |
| Bronze publish | `bronze_<source>_publish` | Validated bronze, safe for downstream reads |
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
- Naming for `silver_<domain>` and `gold_*` tables is TBD (domains not yet
  defined) — decide when the first one is actually built, not speculatively here.

## Bundle resources

- Jobs and pipelines: `<what>_<detail>` (e.g. `seed_neon_ecommerce`,
  `neon_ecommerce_ingestion`, `verify_neon_ecommerce_pattern`), deployed name
  suffixed `-${bundle.target}` (e.g. `neon-ecommerce-ingestion-dev`) so the same
  resource key is distinguishable across `dev`/`tst`/`prd`.
