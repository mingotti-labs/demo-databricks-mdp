# Batch snapshot of bronze_neon.order_items_raw -- see customers_snapshot.py
# for the full write-up on why this must be a batch read, not a stream.
from pyspark import pipelines as dp


@dp.materialized_view()
def order_items_snapshot():
    return spark.read.table("bronze_neon.order_items_raw")
