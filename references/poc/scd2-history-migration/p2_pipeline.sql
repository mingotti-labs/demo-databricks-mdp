-- Probe P2 (pattern-scd2-history-migration): backfill once (as P1b), then keep the
-- SCD2 table current from a materialized view with no timestamp, through a snapshot
-- flow whose version is the view's last refresh time (information_schema last_altered).
CREATE TEMPORARY VIEW asset_history AS
SELECT e.asset_id, e.asset_name, e.asset_owner, e.change_ts, e.is_delete
FROM (
  SELECT explode(
    CASE WHEN l.end_date IS NOT NULL AND l.start_date = last.last_start_date
      THEN array(
        named_struct('asset_id', l.asset_id, 'asset_name', l.asset_name, 'asset_owner', l.asset_owner,
                     'change_ts', CAST(l.start_date AS TIMESTAMP), 'is_delete', false),
        named_struct('asset_id', l.asset_id, 'asset_name', l.asset_name, 'asset_owner', l.asset_owner,
                     'change_ts', CAST(l.end_date AS TIMESTAMP), 'is_delete', true))
      ELSE array(
        named_struct('asset_id', l.asset_id, 'asset_name', l.asset_name, 'asset_owner', l.asset_owner,
                     'change_ts', CAST(l.start_date AS TIMESTAMP), 'is_delete', false))
    END) AS e
  FROM STREAM(mdp_dev.pattern_bronze_publish.zz_p1_legacy) l
  JOIN (
    SELECT asset_id, max(start_date) AS last_start_date
    FROM mdp_dev.pattern_bronze_publish.zz_p1_legacy
    GROUP BY asset_id
  ) last ON l.asset_id = last.asset_id
);

CREATE TEMPORARY VIEW asset_live AS
SELECT asset_id, asset_name, asset_owner FROM mdp_dev.pattern_bronze_publish.zz_p2_source;

CREATE OR REFRESH STREAMING TABLE zz_p2_migrated;

CREATE FLOW backfill_history AS AUTO CDC ONCE INTO zz_p2_migrated
FROM STREAM(asset_history)
KEYS (asset_id)
APPLY AS DELETE WHEN is_delete
SEQUENCE BY change_ts
COLUMNS * EXCEPT (is_delete, change_ts)
STORED AS SCD TYPE 2;

CREATE FLOW live_snapshot AS AUTO CDC INTO zz_p2_migrated
FROM SNAPSHOT (SELECT * FROM asset_live)
WITH VERSION (
  SELECT last_altered AS version
  FROM mdp_dev.information_schema.tables
  WHERE table_schema = 'pattern_bronze_publish' AND table_name = 'zz_p2_source'
    AND (NOT EXISTS (SELECT 1 FROM last_snapshot_version())
         OR last_altered > (SELECT version FROM last_snapshot_version()))
)
KEYS (asset_id)
STORED AS SCD TYPE 2;
