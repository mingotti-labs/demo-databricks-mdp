# Pattern bronze_publish_scd2_autocdc_snapshot_python: SCD Type 2 (full history,
# __START_AT / __END_AT) of a full-load _raw table via snapshot-based Auto CDC.
# `source` points directly at the raw table; the snapshot flow does not need its
# source to be a dataset of this pipeline (confirmed by a real run, not assumed
# from the docs' wrapper-view example). Reference only: the live sources use the
# bronze full pattern (bronze_publish_scd2_autocdc_full_load_python), which also
# keeps raw's platform timestamps out of the snapshot. Reads the dev UNGM codes.
#
# What the Neon source showed (a Lakeflow Connect table maintained by upserts):
# - Streaming create_auto_cdc_flow against an upserted source fails with
#   DELTA_SOURCE_TABLE_IGNORE_CHANGES; a snapshot flow is the pipeline-native fix.
# - skipChangeCommits is not a fix: it silently drops the updated rows.
# - Changing the `source` of a flow that has already run (an intermediate view to
#   the raw table) can insert duplicate no-op versions for unchanged rows (199 of
#   200 customers); a full refresh of the target is the fix and discards history.
from pyspark import pipelines as dp

dp.create_streaming_table(
    name="bronze_publish_scd2_autocdc_snapshot_python",
    table_properties={"delta.enableChangeDataFeed": "true"},
)
dp.create_auto_cdc_from_snapshot_flow(
    target="bronze_publish_scd2_autocdc_snapshot_python",
    source="bronze_ungm.unspsc_public_raw",
    keys=["Id"],
    stored_as_scd_type=2,
)
