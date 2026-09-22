# SCD Type 1 modeling of UNSPSC codes, via snapshot-based Auto CDC.
# `source` points directly at `bronze_ungm.unspsc_public_raw` -- confirmed
# via a real run (against Neon's equivalent pattern) that
# create_auto_cdc_from_snapshot_flow does not require its source to be a
# dataset within this pipeline's own dataflow graph; no intermediate
# snapshot materialized view is needed. See
# phase3b-scd-snapshot-cleanup's design.md.
from pyspark import pipelines as dp

dp.create_streaming_table(name="unspsc_public_scd1")
dp.create_auto_cdc_from_snapshot_flow(
    target="unspsc_public_scd1",
    source="bronze_ungm.unspsc_public_raw",
    keys=["Id"],
    stored_as_scd_type=1,
)
