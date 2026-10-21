-- Auto Loader schema evolution -- none, SQL sibling of
-- python_none/web_events_none.py. Same documented (not independently
-- re-verified) behavior: continues without interruption, new columns are
-- silently dropped (not captured anywhere, not even rescued) -- the
-- riskiest mode, since nothing signals that data was lost. See that file's
-- header for the full behavior/recovery write-up.
--
-- inferColumnTypes => false to match cloudFiles' Python default (all-string).
-- schemaLocation is intentionally NOT set: the pipeline manages it
-- automatically.
CREATE OR REFRESH STREAMING TABLE web_events_none_sql
AS SELECT * FROM STREAM read_files(
  '/Volumes/${clickstream_catalog}/bronze_clickstream/s3_clickstream_raw/web_events/landing',
  format => 'json',
  inferColumnTypes => false,
  schemaEvolutionMode => 'none'
);
