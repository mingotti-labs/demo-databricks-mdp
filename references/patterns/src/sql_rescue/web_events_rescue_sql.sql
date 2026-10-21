-- Auto Loader schema evolution -- rescue, SQL sibling of
-- python_rescue/web_events_rescue.py. Same documented (not independently
-- re-verified) behavior: never fails on a new column, new fields are
-- captured as JSON inside `_rescued_data` instead of becoming real columns.
-- See that file's header for the full behavior/recovery write-up.
--
-- inferColumnTypes => false to match cloudFiles' Python default (all-string).
-- schemaLocation is intentionally NOT set: the pipeline manages it
-- automatically.
CREATE OR REFRESH STREAMING TABLE web_events_rescue_sql
AS SELECT * FROM STREAM read_files(
  '/Volumes/${clickstream_catalog}/bronze_clickstream/s3_clickstream_raw/web_events/landing',
  format => 'json',
  inferColumnTypes => false,
  schemaEvolutionMode => 'rescue'
);
