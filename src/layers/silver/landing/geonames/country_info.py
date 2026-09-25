# SCD2 is the only variant Bronze Publish has for country_info (SCD1
# dropped from phase3j's scope -- see bronze_geonames_publish's design.md).
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.silver_landing import land  # noqa: E402


@dp.materialized_view()
def country_info():
    df = spark.read.table("bronze_geonames_publish.country_info_scd2")
    return land(df, natural_keys=["iso_alpha2"], source_name="geonames", scd2=True)
