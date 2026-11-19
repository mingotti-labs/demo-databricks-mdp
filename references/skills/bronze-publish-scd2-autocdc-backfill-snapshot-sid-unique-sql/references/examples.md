# Examples

## Sample prompts

- "Migrate `main.dw.asset_dim_legacy` (`asset_sid`, SCD2 `start_date`/`end_date`) into `asset_dim_migrated`,
  key `asset_id`, columns `asset_name, asset_owner`, live MV `main.dw.asset_source`; every version needs its
  own sid."
- "Backfill `sales.dim.customer_scd2` with surrogate key `customer_sk` (valid_from/valid_to), keep it current
  from the MV `sales.stage.customer_current`, key `customer_id`, tracked `name, segment`; sids must be unique."
- "Unique sid pattern, composite key `country_code, store_id`, sid `store_sk`, legacy `retail.dim.store_hist`
  (`eff_from`/`eff_to`), live MV `retail.stage.store_mv`, columns `store_name, manager`, target `store_dim`
  in `retail.dim`."

## Filled inputs for the first prompt

As in `bronze-publish-scd2-autocdc-backfill-snapshot-sid-sql`, plus `{{target_catalog}}` = `main`,
`{{target_schema}}` = `dw`, `{{cutover}}` = `2025-05-01`. The view file:

```sql
CREATE OR REPLACE VIEW main.dw.asset_dim_migrated_unique AS
SELECT CASE WHEN __START_AT <= TIMESTAMP'2025-05-01' THEN asset_sid
            ELSE xxhash64(sha2(concat_ws('|', coalesce(asset_id, '<null>'), coalesce(asset_name, '<null>'),
                                         coalesce(asset_owner, '<null>')), 256), __START_AT) END AS asset_sid,
       asset_id, asset_name, asset_owner, __START_AT, __END_AT
FROM main.dw.asset_dim_migrated;
```
