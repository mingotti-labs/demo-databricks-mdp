# SCD Type 1 modeling of Neon's order_items table. SCD1 only -- same
# reasoning as orders_scd1.py.
from pyspark import pipelines as dp

dp.create_streaming_table(name="order_items_scd1")
dp.create_auto_cdc_from_snapshot_flow(
    target="order_items_scd1",
    source="order_items_snapshot",
    keys=["id"],
    stored_as_scd_type=1,
)
