# SCD Type 2 modeling of the ACNC Charity Register -- see charity_register_scd1.py
# for why `source` points at the private charity_register_valid view.
from pyspark import pipelines as dp

dp.create_streaming_table(name="charity_register_scd2")
dp.create_auto_cdc_from_snapshot_flow(
    target="charity_register_scd2",
    source="charity_register_valid",
    keys=["ABN"],
    stored_as_scd_type=2,
)
