# SCD Type 1 modeling of UNSPSC codes, via snapshot-based Auto CDC against
# unspsc_public_snapshot.py's batch read. See that file's header for why
# streaming Auto CDC doesn't work against this source.
from pyspark import pipelines as dp

dp.create_streaming_table(name="unspsc_public_scd1")
dp.create_auto_cdc_from_snapshot_flow(
    target="unspsc_public_scd1",
    source="unspsc_public_snapshot",
    keys=["Id"],
    stored_as_scd_type=1,
)
