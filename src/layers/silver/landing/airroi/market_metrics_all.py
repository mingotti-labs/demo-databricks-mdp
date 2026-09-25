# SCD2 is the only variant Bronze Publish has for market_metrics_all (no
# SCD1 built -- deliberate scope decision, see airroi_publish's design.md).
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.silver_landing import land  # noqa: E402

NATURAL_KEYS = ["_country", "_region", "_locality", "_district", "date"]


@dp.materialized_view()
def market_metrics_all():
    df = spark.read.table("bronze_airroi_publish.market_metrics_all_scd2")
    return land(df, natural_keys=NATURAL_KEYS, source_name="airroi", scd2=True)
