-- Auto Loader schema evolution -- addNewColumns, SQL sibling of the Python
-- canonical (python_add_new_columns/web_events_raw.py). Same confirmed-live
-- behavior applies: the flow terminates once on a new column
-- ("... encountered a schema change during execution and terminated"), and
-- Databricks auto-starts and completes a new update (cause SCHEMA_CHANGE),
-- no human action needed. See that file's header for the full write-up --
-- not repeated here since the underlying behavior is identical, only the
-- authoring language differs.
--
-- inferColumnTypes => false to match cloudFiles' Python default (all-string)
-- -- read_files() defaults inferColumnTypes to true, the opposite of
-- cloudFiles in Python, so this must be set explicitly for a fair
-- side-by-side comparison between the two languages' output schemas.
-- schemaLocation is intentionally NOT set: the pipeline manages it
-- automatically.
CREATE OR REFRESH STREAMING TABLE web_events_add_new_columns_sql
AS SELECT * FROM STREAM read_files(
  '/Volumes/${clickstream_catalog}/bronze_clickstream/s3_clickstream_raw/web_events/landing',
  format => 'json',
  inferColumnTypes => false,
  schemaEvolutionMode => 'addNewColumns'
);
