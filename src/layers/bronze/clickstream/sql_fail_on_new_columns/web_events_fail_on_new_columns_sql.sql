-- Auto Loader schema evolution -- failOnNewColumns, SQL sibling of
-- python_fail_on_new_columns/web_events_fail_on_new_columns.py. Same
-- documented (not independently re-verified) behavior: fails immediately on
-- a new column, does NOT auto-restart -- genuinely manual recovery (update
-- the schema or remove/quarantine the offending file, then re-trigger). See
-- that file's header for the full behavior/recovery write-up.
--
-- inferColumnTypes => false to match cloudFiles' Python default (all-string).
-- schemaLocation is intentionally NOT set: the pipeline manages it
-- automatically.
CREATE OR REFRESH STREAMING TABLE web_events_fail_on_new_columns_sql
AS SELECT * FROM STREAM read_files(
  '/Volumes/${clickstream_catalog}/bronze_clickstream/s3_clickstream_raw/web_events/landing',
  format => 'json',
  inferColumnTypes => false,
  schemaEvolutionMode => 'failOnNewColumns'
);
