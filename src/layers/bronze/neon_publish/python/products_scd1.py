# SCD Type 1 modeling of Neon's products table -- see customers_scd1.py /
# customers_snapshot.py for the full write-up.
from pyspark import pipelines as dp

dp.create_streaming_table(name="products_scd1")
dp.create_auto_cdc_from_snapshot_flow(
    target="products_scd1",
    source="products_snapshot",
    keys=["id"],
    stored_as_scd_type=1,
)
