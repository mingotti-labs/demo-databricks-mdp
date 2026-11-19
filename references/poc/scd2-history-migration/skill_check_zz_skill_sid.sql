-- Pattern bronze_publish_scd2_autocdc_backfill_snapshot_sid_sql: legacy SCD2 history with its
-- surrogate key, then a materialized view without a timestamp (version = its refresh time).
-- Live key: the open legacy key with the same row hash, else xxhash64(row_hash).
CREATE OR REFRESH STREAMING TABLE zz_skill_sid;

CREATE TEMPORARY VIEW zz_skill_sid_history AS
SELECT asset_sid, asset_id, asset_name, asset_owner,
       CAST(start_date AS TIMESTAMP) AS valid_from, CAST(end_date AS TIMESTAMP) AS valid_to,
       sha2(concat_ws('|', coalesce(asset_id, '<null>'), coalesce(asset_name, '<null>'), coalesce(asset_owner, '<null>')), 256) AS row_hash
FROM mdp_dev.pattern_bronze_publish.asset_dim_legacy;

CREATE TEMPORARY VIEW zz_skill_sid_legacy_key AS
SELECT row_hash, asset_sid
FROM (SELECT row_hash, asset_sid, valid_to,
             row_number() OVER (PARTITION BY row_hash ORDER BY valid_from DESC) AS rank
      FROM zz_skill_sid_history)
WHERE rank = 1 AND valid_to IS NULL;

CREATE TEMPORARY VIEW zz_skill_sid_live AS
SELECT coalesce(k.asset_sid, xxhash64(l.row_hash)) AS asset_sid, l.asset_id, l.asset_name, l.asset_owner
FROM (SELECT asset_id, asset_name, asset_owner, sha2(concat_ws('|', coalesce(asset_id, '<null>'), coalesce(asset_name, '<null>'), coalesce(asset_owner, '<null>')), 256) AS row_hash FROM mdp_dev.pattern_bronze_publish.asset_source) l
LEFT JOIN zz_skill_sid_legacy_key k ON k.row_hash = l.row_hash;

CREATE TEMPORARY VIEW zz_skill_sid_union AS
SELECT asset_sid, asset_id, asset_name, asset_owner, valid_from, valid_to, false AS is_live FROM zz_skill_sid_history
UNION ALL
SELECT asset_sid, asset_id, asset_name, asset_owner, CAST(NULL AS TIMESTAMP), CAST(NULL AS TIMESTAMP), true FROM zz_skill_sid_live;

CREATE TEMPORARY VIEW zz_skill_sid_versions AS
SELECT valid_from AS version, false AS is_live FROM zz_skill_sid_history
UNION SELECT valid_to, false FROM zz_skill_sid_history WHERE valid_to IS NOT NULL
UNION SELECT last_altered, true FROM mdp_dev.information_schema.tables
      WHERE table_schema = 'pattern_bronze_publish' AND table_name = 'asset_source';

CREATE TEMPORARY VIEW zz_skill_sid_cutover AS
SELECT max(version) AS last_legacy_version FROM zz_skill_sid_versions WHERE NOT is_live;

CREATE FLOW zz_skill_sid_migrate_and_load AS AUTO CDC INTO zz_skill_sid
FROM SNAPSHOT (
  SELECT u.asset_sid, u.asset_id, u.asset_name, u.asset_owner
  FROM zz_skill_sid_union u CROSS JOIN zz_skill_sid_cutover c
  WHERE CASE WHEN u.is_live
             THEN (SELECT version FROM current_snapshot_version()) > c.last_legacy_version
             ELSE (SELECT version FROM current_snapshot_version()) <= c.last_legacy_version
                  AND u.valid_from <= (SELECT version FROM current_snapshot_version())
                  AND (u.valid_to IS NULL
                       OR u.valid_to > (SELECT version FROM current_snapshot_version())) END
)
WITH VERSION (
  SELECT min(version) AS version FROM zz_skill_sid_versions
  WHERE NOT EXISTS (SELECT 1 FROM last_snapshot_version())
     OR version > (SELECT version FROM last_snapshot_version())
  HAVING min(version) IS NOT NULL
)
KEYS (asset_id)
STORED AS SCD TYPE 2;
