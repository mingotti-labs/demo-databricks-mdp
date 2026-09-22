# SCD Type 1 modeling of Neon's orders table. SCD1 only -- orders is
# transactional, not a dimension; see customers_scd2.py for why full
# history (SCD2) isn't built for it, and customers_scd1.py for why `source`
# points directly at the raw table.
from pyspark import pipelines as dp

dp.create_streaming_table(name="orders_scd1")
dp.create_auto_cdc_from_snapshot_flow(
    target="orders_scd1",
    source="bronze_neon.orders_raw",
    keys=["id"],
    stored_as_scd_type=1,
)
