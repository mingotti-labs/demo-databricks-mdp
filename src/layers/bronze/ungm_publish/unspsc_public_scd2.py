# SCD Type 2 (full history, __START_AT/__END_AT) modeling of UNSPSC codes,
# via snapshot-based Auto CDC -- see unspsc_public_snapshot.py for why
# streaming Auto CDC doesn't work here.
from pyspark import pipelines as dp

dp.create_streaming_table(name="unspsc_public_scd2")
dp.create_auto_cdc_from_snapshot_flow(
    target="unspsc_public_scd2",
    source="unspsc_public_snapshot",
    keys=["Id"],
    stored_as_scd_type=2,
)
