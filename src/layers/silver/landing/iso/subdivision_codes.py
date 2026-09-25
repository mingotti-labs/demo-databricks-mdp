# SCD2 is the only variant Bronze Publish has for subdivision_codes (SCD1
# dropped from phase3i's scope -- see bronze_iso_publish's design.md).
# Keyed by all three columns, not subdivision_code alone -- see
# subdivision_codes_scd2.py for the real-data finding that motivated this.
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.silver_landing import land  # noqa: E402

NATURAL_KEYS = ["subdivision_code", "language_code", "subdivision_name"]


@dp.materialized_view()
def subdivision_codes():
    df = spark.read.table("bronze_iso_publish.subdivision_codes_scd2")
    return land(df, natural_keys=NATURAL_KEYS, source_name="iso", scd2=True)
