# SCD1 is the only variant Bronze Publish has for orders (no SCD2 built --
# transactional/append-heavy, not dimension-like, per neon-scd-modeling's
# design.md). Python variant is canonical over the SQL one.
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.silver_landing import land  # noqa: E402


@dp.materialized_view()
def orders():
    df = spark.read.table("bronze_neon_publish.orders_scd1")
    return land(df, natural_keys=["id"], source_name="neon", scd2=False)
