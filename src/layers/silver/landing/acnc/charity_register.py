# SCD2 selected over SCD1 per silver.md's precedence rule (SCD2 > SCD1 > SCD0).
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.silver_landing import land  # noqa: E402


@dp.materialized_view()
def charity_register():
    df = spark.read.table("bronze_acnc_publish.charity_register_scd2")
    return land(df, natural_keys=["ABN"], source_name="acnc", scd2=True)
