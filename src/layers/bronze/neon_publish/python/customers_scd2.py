# SCD Type 2 (full history, __START_AT/__END_AT) modeling of Neon's
# customers table -- see customers_scd1.py for why `source` points directly
# at bronze_neon.customers_raw (no intermediate snapshot view needed,
# confirmed via a real run). Only customers and products get SCD2 -- orders
# and order_items are transactional/append-heavy, not dimension-like, so
# tracking their full change history isn't meaningful the way it is here.
from pyspark import pipelines as dp

dp.create_streaming_table(name="customers_scd2")
dp.create_auto_cdc_from_snapshot_flow(
    target="customers_scd2",
    source="bronze_neon.customers_raw",
    keys=["id"],
    stored_as_scd_type=2,
)
