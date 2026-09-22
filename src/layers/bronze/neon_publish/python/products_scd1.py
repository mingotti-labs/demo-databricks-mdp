# SCD Type 1 modeling of Neon's products table -- see customers_scd1.py for
# the full write-up on why `source` points directly at the raw table.
from pyspark import pipelines as dp

dp.create_streaming_table(name="products_scd1")
dp.create_auto_cdc_from_snapshot_flow(
    target="products_scd1",
    source="bronze_neon.products_raw",
    keys=["id"],
    stored_as_scd_type=1,
)
