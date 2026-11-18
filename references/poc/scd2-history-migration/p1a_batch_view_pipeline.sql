-- Probe P1 (pattern-scd2-history-migration): backfill an SCD2 table once with
-- AUTO CDC ONCE from a batch temporary view over the legacy SCD2 table.
CREATE TEMPORARY VIEW asset_history AS
SELECT asset_id, asset_name, asset_owner, CAST(start_date AS TIMESTAMP) AS change_ts, false AS is_delete
FROM mdp_dev.pattern_bronze_publish.zz_p1_legacy
UNION ALL
SELECT l.asset_id, l.asset_name, l.asset_owner, CAST(l.end_date AS TIMESTAMP), true
FROM mdp_dev.pattern_bronze_publish.zz_p1_legacy l
WHERE l.end_date IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM mdp_dev.pattern_bronze_publish.zz_p1_legacy n
    WHERE n.asset_id = l.asset_id AND n.start_date > l.start_date
  );

CREATE OR REFRESH STREAMING TABLE zz_p1_migrated;

CREATE FLOW backfill_history AS AUTO CDC ONCE INTO zz_p1_migrated
FROM asset_history
KEYS (asset_id)
APPLY AS DELETE WHEN is_delete
SEQUENCE BY change_ts
COLUMNS * EXCEPT (is_delete, change_ts)
STORED AS SCD TYPE 2;
