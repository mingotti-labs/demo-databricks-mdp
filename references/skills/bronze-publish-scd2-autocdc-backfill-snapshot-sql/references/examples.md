# Examples

## Sample prompts

- "Migrate `main.dw.asset_dim_legacy` (SCD2, `start_date`/`end_date`) into `asset_dim_migrated`, key
  `asset_id`, columns `asset_name, asset_owner`; live source is the materialized view `main.dw.asset_source`."
- "Write the pipeline SQL to backfill `sales.dim.customer_scd2` (valid_from/valid_to) with its history and
  keep it current from the MV `sales.stage.customer_current`, key `customer_id`, tracked `name, segment`."
- "Snapshot pattern, composite key `country_code, store_id`, legacy `retail.dim.store_hist`, live MV
  `retail.stage.store_mv`, columns `store_name, manager`, dates `eff_from`/`eff_to`, target `store_dim`."

## Filled inputs for the first prompt

`{{target}}` = `asset_dim_migrated`, `{{legacy_table}}` = `main.dw.asset_dim_legacy`,
`{{source_table}}` = `main.dw.asset_source` (catalog `main`, schema `dw`, name `asset_source`),
`{{keys}}` = `asset_id`, `{{columns}}` = `asset_id, asset_name, asset_owner`,
`{{u_columns}}` = `u.asset_id, u.asset_name, u.asset_owner`,
`{{start_col}}` = `start_date`, `{{end_col}}` = `end_date`.

## Composite key

`{{keys}}` = `country_code, store_id`; both also lead `{{columns}}`:
`country_code, store_id, store_name, manager`. Nothing else in the template changes.
