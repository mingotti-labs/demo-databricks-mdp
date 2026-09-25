# SCD1 is the only variant Bronze Publish has for order_items (same reasoning
# as orders.py). Python variant is canonical over the SQL one.
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.silver_landing import land  # noqa: E402


@dp.materialized_view()
def order_items():
    df = spark.read.table("bronze_neon_publish.order_items_scd1")
    return land(df, natural_keys=["id"], source_name="neon", scd2=False)
