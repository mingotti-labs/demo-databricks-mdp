-- Probe P3 (pattern-scd2-history-migration): once-only backfill (as P1b) plus a live
-- AUTO CDC ONCE from a streaming temporary view over the legacy SCD2 table.
-- P1a showed the source must be a streaming query, even for ONCE.
-- A retired asset (last version closed) also emits a delete event at its end_date;
-- the last start_date per asset comes from a static lookup (stream-static join).
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

CREATE OR REFRESH STREAMING TABLE zz_p3_migrated;

CREATE FLOW backfill_history AS AUTO CDC ONCE INTO zz_p3_migrated
FROM STREAM(asset_history)
KEYS (asset_id)
APPLY AS DELETE WHEN is_delete
SEQUENCE BY change_ts
COLUMNS * EXCEPT (is_delete, change_ts)
STORED AS SCD TYPE 2;

-- Live: an append-only source without a timestamp; the change feed gives each row's commit time.
CREATE TEMPORARY VIEW asset_live AS
SELECT asset_id, asset_name, asset_owner, _commit_timestamp AS change_ts, false AS is_delete
FROM STREAM(mdp_dev.pattern_bronze_publish.zz_p3_source) WITH (readChangeFeed = true)
WHERE _change_type = 'insert';

CREATE FLOW live_stream AS AUTO CDC INTO zz_p3_migrated
FROM STREAM(asset_live)
KEYS (asset_id)
APPLY AS DELETE WHEN is_delete
SEQUENCE BY change_ts
COLUMNS * EXCEPT (is_delete, change_ts)
STORED AS SCD TYPE 2;
