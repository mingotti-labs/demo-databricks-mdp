# SCD Type 1 modeling of the ACNC Charity Register, via snapshot-based Auto
# CDC against the private charity_register_valid view (see its header for
# why a filtered intermediate dataset is needed here, unlike Neon/UNGM's
# direct-to-raw pattern).
from pyspark import pipelines as dp

dp.create_streaming_table(name="charity_register_scd1")
dp.create_auto_cdc_from_snapshot_flow(
    target="charity_register_scd1",
    source="charity_register_valid",
    keys=["ABN"],
    stored_as_scd_type=1,
)
