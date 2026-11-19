-- Pattern bronze_publish_scd2_autocdc_backfill_snapshot_sid_unique_sql (pipeline part): legacy SCD2 history with its
-- surrogate key, then a materialized view without a timestamp (version = its refresh time).
-- Live key: the open legacy key with the same row hash, else xxhash64(row_hash).
CREATE OR REFRESH STREAMING TABLE {{target}};

CREATE TEMPORARY VIEW {{target}}_history AS
SELECT {{sid}}, {{columns}},
       CAST({{start_col}} AS TIMESTAMP) AS valid_from, CAST({{end_col}} AS TIMESTAMP) AS valid_to,
       {{row_hash}} AS row_hash
FROM {{legacy_table}};

CREATE TEMPORARY VIEW {{target}}_legacy_key AS
SELECT row_hash, {{sid}}
FROM (SELECT row_hash, {{sid}}, valid_to,
             row_number() OVER (PARTITION BY row_hash ORDER BY valid_from DESC) AS rank
      FROM {{target}}_history)
WHERE rank = 1 AND valid_to IS NULL;

CREATE TEMPORARY VIEW {{target}}_live AS
SELECT coalesce(k.{{sid}}, xxhash64(l.row_hash)) AS {{sid}}, {{l_columns}}
FROM (SELECT {{columns}}, {{row_hash}} AS row_hash FROM {{source_table}}) l
LEFT JOIN {{target}}_legacy_key k ON k.row_hash = l.row_hash;

CREATE TEMPORARY VIEW {{target}}_union AS
SELECT {{sid}}, {{columns}}, valid_from, valid_to, false AS is_live FROM {{target}}_history
UNION ALL
SELECT {{sid}}, {{columns}}, CAST(NULL AS TIMESTAMP), CAST(NULL AS TIMESTAMP), true FROM {{target}}_live;

CREATE TEMPORARY VIEW {{target}}_versions AS
SELECT valid_from AS version, false AS is_live FROM {{target}}_history
UNION SELECT valid_to, false FROM {{target}}_history WHERE valid_to IS NOT NULL
UNION SELECT last_altered, true FROM {{source_catalog}}.information_schema.tables
      WHERE table_schema = '{{source_schema}}' AND table_name = '{{source_name}}';

CREATE TEMPORARY VIEW {{target}}_cutover AS
SELECT max(version) AS last_legacy_version FROM {{target}}_versions WHERE NOT is_live;

CREATE FLOW {{target}}_migrate_and_load AS AUTO CDC INTO {{target}}
FROM SNAPSHOT (
  SELECT u.{{sid}}, {{u_columns}}
  FROM {{target}}_union u CROSS JOIN {{target}}_cutover c
  WHERE CASE WHEN u.is_live
             THEN (SELECT version FROM current_snapshot_version()) > c.last_legacy_version
             ELSE (SELECT version FROM current_snapshot_version()) <= c.last_legacy_version
                  AND u.valid_from <= (SELECT version FROM current_snapshot_version())
                  AND (u.valid_to IS NULL
                       OR u.valid_to > (SELECT version FROM current_snapshot_version())) END
)
WITH VERSION (
  SELECT min(version) AS version FROM {{target}}_versions
  WHERE NOT EXISTS (SELECT 1 FROM last_snapshot_version())
     OR version > (SELECT version FROM last_snapshot_version())
  HAVING min(version) IS NOT NULL
)
KEYS ({{keys}})
STORED AS SCD TYPE 2;
