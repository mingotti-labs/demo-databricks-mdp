# Pattern bronze_publish_scd1_autocdc_snapshot_python: SCD Type 1 (latest value
# per key) of a full-load _raw table, via snapshot-based Auto CDC. `source` points
# directly at the raw table; the snapshot flow does not need its source to be a
# dataset of this pipeline. Reference only: no live source builds an SCD1 table
# from a full load any more (the SCD2 table gives the same with
# `WHERE __END_AT IS NULL`). Reads the dev UNGM UNSPSC codes.
from pyspark import pipelines as dp

dp.create_streaming_table(name="bronze_publish_scd1_autocdc_snapshot_python")
dp.create_auto_cdc_from_snapshot_flow(
    target="bronze_publish_scd1_autocdc_snapshot_python",
    source="bronze_ungm.unspsc_public_raw",
    keys=["Id"],
    stored_as_scd_type=1,
)
