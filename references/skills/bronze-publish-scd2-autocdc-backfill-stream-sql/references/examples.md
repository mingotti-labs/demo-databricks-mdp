# Examples

## Sample prompts

- "Migrate `main.dw.asset_dim_legacy` (SCD2, `start_date`/`end_date`) into `asset_dim_migrated`, key
  `asset_id`, columns `asset_name, asset_owner`; new rows are appended to `main.dw.asset_source`."
- "Backfill `crm.dim.contact_hist` (valid_from/valid_to) with history into `contact_dim`, then load changes
  from the append-only table `crm.raw.contact_feed`, key `contact_id`, tracked `email, region`."
- "Stream pattern, composite key `country_code, store_id`, legacy `retail.dim.store_hist`
  (`eff_from`/`eff_to`), append-only source `retail.raw.store_events`, columns `store_name, manager`."

## Filled inputs for the first prompt

`{{target}}` = `asset_dim_migrated`, `{{legacy_table}}` = `main.dw.asset_dim_legacy`,
`{{source_table}}` = `main.dw.asset_source`, `{{keys}}` = `asset_id`,
`{{columns}}` = `asset_id, asset_name, asset_owner`,
`{{e_columns}}` = `e.asset_id, e.asset_name, e.asset_owner`,
`{{struct_columns}}` = `'asset_id', l.asset_id, 'asset_name', l.asset_name, 'asset_owner', l.asset_owner`,
`{{key_join}}` = `l.asset_id = last.asset_id`, `{{start_col}}` = `start_date`, `{{end_col}}` = `end_date`.

## Composite key

`{{keys}}` = `country_code, store_id`; `{{key_join}}` =
`l.country_code = last.country_code AND l.store_id = last.store_id`.
