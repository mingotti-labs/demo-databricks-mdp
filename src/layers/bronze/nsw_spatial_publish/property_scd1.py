# SCD Type 1 modeling of NSW Spatial Services' Property layer, via
# snapshot-based Auto CDC directly against bronze_nsw_spatial.property_raw
# (no intermediate view needed -- see property_scd2.py for the full
# write-up on why `addressstringoid`, not `propid`, is the key).
from pyspark import pipelines as dp

dp.create_streaming_table(name="property_scd1")
dp.create_auto_cdc_from_snapshot_flow(
    target="property_scd1",
    source="bronze_nsw_spatial.property_raw",
    keys=["addressstringoid"],
    stored_as_scd_type=1,
)
