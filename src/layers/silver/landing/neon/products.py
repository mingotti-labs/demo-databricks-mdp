# SCD2 selected over SCD1 per silver.md's precedence rule (SCD2 > SCD1 > SCD0).
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.silver_landing import land  # noqa: E402


@dp.materialized_view()
def products():
    df = spark.read.table("bronze_neon_publish.products_scd2")
    return land(df, natural_keys=["id"], source_name="neon", scd2=True)
