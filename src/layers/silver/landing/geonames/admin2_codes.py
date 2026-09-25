# SCD2 is the only variant Bronze Publish has for admin2_codes (SCD1
# dropped from phase3j's scope -- see bronze_geonames_publish's design.md).
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.silver_landing import land  # noqa: E402


@dp.materialized_view()
def admin2_codes():
    df = spark.read.table("bronze_geonames_publish.admin2_codes_scd2")
    return land(df, natural_keys=["code"], source_name="geonames", scd2=True)
