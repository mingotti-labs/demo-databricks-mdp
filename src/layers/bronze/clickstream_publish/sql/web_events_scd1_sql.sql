-- SCD Type 1 modeling of clickstream events, SQL sibling of
-- python/web_events_scd1.py. web_events_raw is append-only, so plain
-- streaming AUTO CDC works directly -- unlike Neon's SQL SCD2, no
-- MERGE-based job workaround is needed here.
CREATE OR REFRESH STREAMING TABLE web_events_scd1_sql;

CREATE FLOW web_events_scd1_sql_flow AS AUTO CDC INTO web_events_scd1_sql
FROM STREAM(bronze_clickstream.web_events_raw)
KEYS (event_id)
SEQUENCE BY `timestamp`
STORED AS SCD TYPE 1;
