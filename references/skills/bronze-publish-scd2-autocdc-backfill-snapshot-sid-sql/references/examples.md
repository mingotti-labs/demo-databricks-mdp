# Examples

## Sample prompts

- "Migrate `main.dw.asset_dim_legacy` (`asset_sid`, SCD2 `start_date`/`end_date`) into `asset_dim_migrated`,
  key `asset_id`, columns `asset_name, asset_owner`; live source is the MV `main.dw.asset_source`; keep the sids."
- "Backfill `sales.dim.customer_scd2` with its surrogate key `customer_sk` (valid_from/valid_to) and keep it
  current from the MV `sales.stage.customer_current`, key `customer_id`, tracked `name, segment`."
- "Snapshot sid pattern, composite key `country_code, store_id`, sid `store_sk`, legacy `retail.dim.store_hist`
  (`eff_from`/`eff_to`), live MV `retail.stage.store_mv`, columns `store_name, manager`, target `store_dim`."

## Filled inputs for the first prompt

`{{target}}` = `asset_dim_migrated`, `{{legacy_table}}` = `main.dw.asset_dim_legacy`,
`{{source_table}}` = `main.dw.asset_source` (catalog `main`, schema `dw`, name `asset_source`),
`{{sid}}` = `asset_sid`, `{{keys}}` = `asset_id`, `{{columns}}` = `asset_id, asset_name, asset_owner`,
`{{u_columns}}` = `u.asset_id, u.asset_name, u.asset_owner`, `{{l_columns}}` = `l.asset_id, l.asset_name, l.asset_owner`,
`{{start_col}}` = `start_date`, `{{end_col}}` = `end_date`,
`{{row_hash}}` = `sha2(concat_ws('|', coalesce(asset_id, '<null>'), coalesce(asset_name, '<null>'), coalesce(asset_owner, '<null>')), 256)`.
