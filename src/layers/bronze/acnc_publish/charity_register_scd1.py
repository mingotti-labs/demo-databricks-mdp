# SCD Type 1 modeling of the ACNC Charity Register, via snapshot-based Auto
# CDC against the private charity_register_valid view (see its header for
# why a filtered intermediate dataset is needed here, unlike Neon/UNGM's
# direct-to-raw pattern).
from pyspark import pipelines as dp

dp.create_streaming_table(
    name="bronze_acnc_publish.charity_register_scd1",
    table_properties={
        "delta.enableRowTracking": "true",
        "delta.enableChangeDataFeed": "true",
    },
)
dp.create_auto_cdc_from_snapshot_flow(
    target="bronze_acnc_publish.charity_register_scd1",
    source="charity_register_valid",
    keys=["ABN"],
    stored_as_scd_type=1,
)
