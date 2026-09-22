# SCD Type 2 (full history, __START_AT/__END_AT) modeling of UNSPSC codes
# -- see unspsc_public_scd1.py for why `source` points directly at the raw
# table.
from pyspark import pipelines as dp

dp.create_streaming_table(name="unspsc_public_scd2")
dp.create_auto_cdc_from_snapshot_flow(
    target="unspsc_public_scd2",
    source="bronze_ungm.unspsc_public_raw",
    keys=["Id"],
    stored_as_scd_type=2,
)
