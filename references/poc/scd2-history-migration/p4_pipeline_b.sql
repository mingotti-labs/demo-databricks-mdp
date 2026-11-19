-- Probe P4, variant B (pattern-scd2-history-migration): surrogate key copied from the legacy
-- SCD2 table, new key for new versions. Variant B reads the target's own current rows to tell
-- an unchanged row from one that changed back to an earlier state.
-- Legacy and live rows are inline (no source tables: quota); p4.py replaces __LIVE_ROWS__ and
-- __LIVE_VERSION__ before each update.
CREATE TEMPORARY VIEW asset_history AS
SELECT asset_sid, asset_id, asset_name, asset_owner,
       CAST(start_date AS TIMESTAMP) AS valid_from, CAST(end_date AS TIMESTAMP) AS valid_to,
       sha2(concat_ws('|', coalesce(asset_id, '<null>'), coalesce(asset_name, '<null>'),
                      coalesce(asset_owner, '<null>')), 256) AS row_hash
FROM VALUES
  (101L, 'A1', 'Pump',  'Ann', DATE'2024-01-01', DATE'2024-06-01'),
  (102L, 'A1', 'Pump',  'Bob', DATE'2024-06-01', DATE'2025-01-15'),
  (103L, 'A1', 'Pump',  'Cid', DATE'2025-01-15', CAST(NULL AS DATE)),
  (201L, 'A2', 'Valve', 'Cy',  DATE'2024-02-01', DATE'2024-09-01'),
  (202L, 'A2', 'Valve', 'Dan', DATE'2024-09-01', DATE'2025-03-01'),
  (301L, 'A3', 'Fan',   'Eli', DATE'2024-03-01', DATE'2024-08-01'),
  (302L, 'A3', 'Fan',   'Di',  DATE'2024-08-01', DATE'2025-05-01'),
  (303L, 'A3', 'Fan',   'Eli', DATE'2025-05-01', CAST(NULL AS DATE)),
  (401L, 'A4', 'Belt',  'Flo', DATE'2024-04-01', DATE'2024-10-01'),
  (402L, 'A4', 'Belt',  'Gil', DATE'2024-10-01', CAST(NULL AS DATE))
  AS t(asset_sid, asset_id, asset_name, asset_owner, start_date, end_date);

CREATE TEMPORARY VIEW asset_live_rows AS
SELECT asset_id, asset_name, asset_owner,
       sha2(concat_ws('|', coalesce(asset_id, '<null>'), coalesce(asset_name, '<null>'),
                      coalesce(asset_owner, '<null>')), 256) AS row_hash
FROM VALUES __LIVE_ROWS__ AS t(asset_id, asset_name, asset_owner);

CREATE TEMPORARY VIEW asset_legacy_key AS
SELECT row_hash, asset_sid
FROM (SELECT row_hash, asset_sid, valid_to,
             row_number() OVER (PARTITION BY row_hash ORDER BY valid_from DESC) AS rank
      FROM asset_history)
WHERE rank = 1 AND valid_to IS NULL;

-- Variant B: the target's current rows decide. Unchanged since the last load: keep its key;
-- no current row yet: the legacy lookup; otherwise a new key from the row hash and the version.
CREATE TEMPORARY VIEW asset_current AS
SELECT asset_id, asset_sid,
       sha2(concat_ws('|', coalesce(asset_id, '<null>'), coalesce(asset_name, '<null>'),
                      coalesce(asset_owner, '<null>')), 256) AS row_hash
FROM mdp_dev.pattern_bronze_publish.zz_p4_migrated WHERE __END_AT IS NULL;

CREATE TEMPORARY VIEW asset_live AS
SELECT CASE WHEN c.row_hash = l.row_hash THEN c.asset_sid
            WHEN c.asset_id IS NULL AND k.asset_sid IS NOT NULL THEN k.asset_sid
            ELSE xxhash64(l.row_hash, TIMESTAMP'__LIVE_VERSION__') END AS asset_sid,
       l.asset_id, l.asset_name, l.asset_owner
FROM asset_live_rows l
LEFT JOIN asset_current c ON c.asset_id = l.asset_id
LEFT JOIN asset_legacy_key k ON k.row_hash = l.row_hash;

CREATE TEMPORARY VIEW asset_union AS
SELECT asset_sid, asset_id, asset_name, asset_owner, valid_from, valid_to, false AS is_live
FROM asset_history
UNION ALL
SELECT asset_sid, asset_id, asset_name, asset_owner, CAST(NULL AS TIMESTAMP), CAST(NULL AS TIMESTAMP), true
FROM asset_live;

CREATE TEMPORARY VIEW asset_versions AS
SELECT valid_from AS version, false AS is_live FROM asset_history
UNION SELECT valid_to, false FROM asset_history WHERE valid_to IS NOT NULL
UNION SELECT TIMESTAMP'__LIVE_VERSION__', true;

CREATE TEMPORARY VIEW asset_cutover AS
SELECT max(version) AS last_legacy_version FROM asset_versions WHERE NOT is_live;

CREATE OR REFRESH STREAMING TABLE zz_p4_migrated;

CREATE FLOW migrate_and_load AS AUTO CDC INTO zz_p4_migrated
FROM SNAPSHOT (
  SELECT u.asset_sid, u.asset_id, u.asset_name, u.asset_owner
  FROM asset_union u CROSS JOIN asset_cutover c
  WHERE CASE WHEN u.is_live
             THEN (SELECT version FROM current_snapshot_version()) > c.last_legacy_version
             ELSE (SELECT version FROM current_snapshot_version()) <= c.last_legacy_version
                  AND u.valid_from <= (SELECT version FROM current_snapshot_version())
                  AND (u.valid_to IS NULL
                       OR u.valid_to > (SELECT version FROM current_snapshot_version())) END
)
WITH VERSION (
  SELECT min(version) AS version FROM asset_versions
  WHERE NOT EXISTS (SELECT 1 FROM last_snapshot_version())
     OR version > (SELECT version FROM last_snapshot_version())
  HAVING min(version) IS NOT NULL
)
KEYS (asset_id)
STORED AS SCD TYPE 2;
