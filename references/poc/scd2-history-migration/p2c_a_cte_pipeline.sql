-- Probe P2c (pattern-scd2-history-migration): one snapshot flow WITH VERSION does the
-- backfill (one snapshot per legacy date) and then the live loads (one snapshot per
-- refresh of a materialized view without a timestamp). P2 showed a snapshot target
-- takes no second flow.
CREATE TEMPORARY VIEW asset_history AS
SELECT asset_id, asset_name, asset_owner,
       CAST(start_date AS TIMESTAMP) AS valid_from, CAST(end_date AS TIMESTAMP) AS valid_to
FROM mdp_dev.pattern_bronze_publish.zz_p1_legacy;

CREATE TEMPORARY VIEW asset_live AS
SELECT asset_id, asset_name, asset_owner FROM mdp_dev.pattern_bronze_publish.zz_p2c_source;

CREATE TEMPORARY VIEW asset_union AS
SELECT asset_id, asset_name, asset_owner, valid_from, valid_to, false AS is_live FROM asset_history
UNION ALL
SELECT asset_id, asset_name, asset_owner, CAST(NULL AS TIMESTAMP), CAST(NULL AS TIMESTAMP), true
FROM asset_live;

CREATE TEMPORARY VIEW asset_versions AS
SELECT valid_from AS version, false AS is_live FROM asset_history
UNION SELECT valid_to, false FROM asset_history WHERE valid_to IS NOT NULL
UNION SELECT last_altered, true FROM mdp_dev.information_schema.tables
      WHERE table_schema = 'pattern_bronze_publish' AND table_name = 'zz_p2c_source';

CREATE TEMPORARY VIEW asset_cutover AS
SELECT max(version) AS last_legacy_version FROM asset_versions WHERE NOT is_live;

CREATE OR REFRESH STREAMING TABLE zz_p2c_migrated;

CREATE FLOW migrate_and_load AS AUTO CDC INTO zz_p2c_migrated
FROM SNAPSHOT (
  WITH cur AS (SELECT version AS v FROM current_snapshot_version())
  SELECT u.asset_id, u.asset_name, u.asset_owner
  FROM asset_union u CROSS JOIN cur CROSS JOIN asset_cutover c
  WHERE CASE WHEN u.is_live THEN cur.v > c.last_legacy_version
             ELSE cur.v <= c.last_legacy_version AND u.valid_from <= cur.v
                  AND (u.valid_to IS NULL OR u.valid_to > cur.v) END
)
WITH VERSION (
  SELECT min(version) AS version FROM asset_versions
  WHERE NOT EXISTS (SELECT 1 FROM last_snapshot_version())
     OR version > (SELECT version FROM last_snapshot_version())
  HAVING min(version) IS NOT NULL
)
KEYS (asset_id)
STORED AS SCD TYPE 2;
