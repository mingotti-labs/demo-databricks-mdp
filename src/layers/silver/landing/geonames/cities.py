# SCD2 is the only variant Bronze Publish has for cities (SCD1 dropped
# from phase3j's scope -- see bronze_geonames_publish's design.md).
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.silver_landing import land  # noqa: E402


@dp.materialized_view()
def cities():
    df = spark.read.table("bronze_geonames_publish.cities_scd2")
    return land(df, natural_keys=["geonameid"], source_name="geonames", scd2=True)
