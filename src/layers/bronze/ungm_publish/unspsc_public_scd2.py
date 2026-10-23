# SCD Type 2 (full history, __START_AT/__END_AT) modeling of UNSPSC codes
# -- see unspsc_public_scd1.py for why `source` points directly at the raw
# table. Change data feed feeds Silver Landing (the bronze full pattern,
# openspec rollout-bronze-full-pattern); raw has no per-load column, so the
# snapshot is raw as is.
from pyspark import pipelines as dp

dp.create_streaming_table(
    name="bronze_ungm_publish.unspsc_public_scd2",
    table_properties={
        "pipelines.reset.allowed": "false",
        "delta.enableChangeDataFeed": "true",
    },
)
dp.create_auto_cdc_from_snapshot_flow(
    target="bronze_ungm_publish.unspsc_public_scd2",
    source="bronze_ungm.unspsc_public_raw",
    keys=["Id"],
    stored_as_scd_type=2,
)
