# SCD2 is the only variant Bronze Publish has for country_codes (SCD1
# dropped from phase3i's scope -- see bronze_iso_publish's design.md).
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.silver_landing import land  # noqa: E402


@dp.materialized_view()
def country_codes():
    df = spark.read.table("bronze_iso_publish.country_codes_scd2")
    return land(df, natural_keys=["country_code_alpha2"], source_name="iso", scd2=True)
