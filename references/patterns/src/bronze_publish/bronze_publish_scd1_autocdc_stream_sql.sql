-- Pattern bronze_publish_scd1_autocdc_stream_sql: SCD Type 1 with streaming AUTO
-- CDC in SQL. Valid only against an append-only source (the add_new_columns Auto Loader table is one);
-- against an upserted source it fails with DELTA_SOURCE_TABLE_IGNORE_CHANGES.
-- Reference only. Reads pattern_bronze.autoloader_add_new_columns_python: run that pattern first.
CREATE OR REFRESH STREAMING TABLE bronze_publish_scd1_autocdc_stream_sql;

CREATE FLOW bronze_publish_scd1_autocdc_stream_sql_flow AS AUTO CDC INTO bronze_publish_scd1_autocdc_stream_sql
FROM STREAM(pattern_bronze.autoloader_add_new_columns_python)
KEYS (event_id)
SEQUENCE BY `timestamp`
STORED AS SCD TYPE 1;
