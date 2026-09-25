# SCD2 selected over SCD1 per silver.md's precedence rule (SCD2 > SCD1 > SCD0).
# Function named property_landing, not property, to avoid shadowing the
# Python builtin; explicit name= sets the actual table name.
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.silver_landing import land  # noqa: E402


@dp.materialized_view(name="property")
def property_landing():
    df = spark.read.table("bronze_nsw_spatial_publish.property_scd2")
    return land(df, natural_keys=["addressstringoid"], source_name="nsw_spatial", scd2=True)
