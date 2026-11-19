-- Pattern bronze_publish_scd2_autocdc_backfill_stream_sql: legacy SCD2 history once, then an
-- append-only table without a timestamp (sequence = commit time from its change feed).
CREATE OR REFRESH STREAMING TABLE {{target}};

CREATE TEMPORARY VIEW {{target}}_history AS
SELECT {{e_columns}}, e.change_ts, e.is_delete
FROM (
  SELECT explode(
    CASE WHEN l.{{end_col}} IS NOT NULL AND l.{{start_col}} = last.last_start
      THEN array(
        named_struct({{struct_columns}},
                     'change_ts', CAST(l.{{start_col}} AS TIMESTAMP), 'is_delete', false),
        named_struct({{struct_columns}},
                     'change_ts', CAST(l.{{end_col}} AS TIMESTAMP), 'is_delete', true))
      ELSE array(
        named_struct({{struct_columns}},
                     'change_ts', CAST(l.{{start_col}} AS TIMESTAMP), 'is_delete', false))
    END) AS e
  FROM STREAM({{legacy_table}}) l
  JOIN (SELECT {{keys}}, max({{start_col}}) AS last_start FROM {{legacy_table}} GROUP BY {{keys}}) last
    ON {{key_join}}
);

CREATE FLOW {{target}}_backfill_history AS AUTO CDC ONCE INTO {{target}}
FROM STREAM({{target}}_history)
KEYS ({{keys}})
APPLY AS DELETE WHEN is_delete
SEQUENCE BY change_ts
COLUMNS * EXCEPT (is_delete, change_ts)
STORED AS SCD TYPE 2;

CREATE TEMPORARY VIEW {{target}}_live AS
SELECT {{columns}}, _commit_timestamp AS change_ts, false AS is_delete
FROM STREAM({{source_table}}) WITH (readChangeFeed = true)
WHERE _change_type = 'insert';

CREATE FLOW {{target}}_live_stream AS AUTO CDC INTO {{target}}
FROM STREAM({{target}}_live)
KEYS ({{keys}})
APPLY AS DELETE WHEN is_delete
SEQUENCE BY change_ts
COLUMNS * EXCEPT (is_delete, change_ts)
STORED AS SCD TYPE 2;
