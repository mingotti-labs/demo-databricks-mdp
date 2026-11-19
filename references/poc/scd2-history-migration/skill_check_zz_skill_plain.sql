-- Pattern bronze_publish_scd2_autocdc_backfill_snapshot_sql: legacy SCD2 history, then a
-- materialized view without a timestamp (version = its refresh time).
CREATE OR REFRESH STREAMING TABLE zz_skill_plain;

CREATE TEMPORARY VIEW zz_skill_plain_history AS
SELECT asset_id, asset_name, asset_owner,
       CAST(start_date AS TIMESTAMP) AS valid_from, CAST(end_date AS TIMESTAMP) AS valid_to
FROM mdp_dev.pattern_bronze_publish.asset_dim_legacy;

CREATE TEMPORARY VIEW zz_skill_plain_live AS
SELECT asset_id, asset_name, asset_owner FROM mdp_dev.pattern_bronze_publish.asset_source;

CREATE TEMPORARY VIEW zz_skill_plain_union AS
SELECT asset_id, asset_name, asset_owner, valid_from, valid_to, false AS is_live FROM zz_skill_plain_history
UNION ALL
SELECT asset_id, asset_name, asset_owner, CAST(NULL AS TIMESTAMP), CAST(NULL AS TIMESTAMP), true FROM zz_skill_plain_live;

CREATE TEMPORARY VIEW zz_skill_plain_versions AS
SELECT valid_from AS version, false AS is_live FROM zz_skill_plain_history
UNION SELECT valid_to, false FROM zz_skill_plain_history WHERE valid_to IS NOT NULL
UNION SELECT last_altered, true FROM mdp_dev.information_schema.tables
      WHERE table_schema = 'pattern_bronze_publish' AND table_name = 'asset_source';

CREATE TEMPORARY VIEW zz_skill_plain_cutover AS
SELECT max(version) AS last_legacy_version FROM zz_skill_plain_versions WHERE NOT is_live;

CREATE FLOW zz_skill_plain_migrate_and_load AS AUTO CDC INTO zz_skill_plain
FROM SNAPSHOT (
  SELECT u.asset_id, u.asset_name, u.asset_owner
  FROM zz_skill_plain_union u CROSS JOIN zz_skill_plain_cutover c
  WHERE CASE WHEN u.is_live
             THEN (SELECT version FROM current_snapshot_version()) > c.last_legacy_version
             ELSE (SELECT version FROM current_snapshot_version()) <= c.last_legacy_version
                  AND u.valid_from <= (SELECT version FROM current_snapshot_version())
                  AND (u.valid_to IS NULL
                       OR u.valid_to > (SELECT version FROM current_snapshot_version())) END
)
WITH VERSION (
  SELECT min(version) AS version FROM zz_skill_plain_versions
  WHERE NOT EXISTS (SELECT 1 FROM last_snapshot_version())
     OR version > (SELECT version FROM last_snapshot_version())
  HAVING min(version) IS NOT NULL
)
KEYS (asset_id)
STORED AS SCD TYPE 2;
