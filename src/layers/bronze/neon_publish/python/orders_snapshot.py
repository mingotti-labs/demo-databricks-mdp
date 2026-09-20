# Batch snapshot of bronze_neon.orders_raw -- see customers_snapshot.py for
# the full write-up on why this must be a batch read, not a stream.
from pyspark import pipelines as dp


@dp.materialized_view()
def orders_snapshot():
    return spark.read.table("bronze_neon.orders_raw")
