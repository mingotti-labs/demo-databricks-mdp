# SCD Type 2 modeling of Neon's products table -- see customers_scd2.py for
# why only customers and products get SCD2.
from pyspark import pipelines as dp

dp.create_streaming_table(name="products_scd2")
dp.create_auto_cdc_from_snapshot_flow(
    target="products_scd2",
    source="products_snapshot",
    keys=["id"],
    stored_as_scd_type=2,
)
