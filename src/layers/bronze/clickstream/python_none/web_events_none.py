# Auto Loader schema evolution -- none.
#
# Behavior (Databricks docs -- not independently re-verified via a live run
# here, per direct instruction: only addNewColumns was exercised for real):
# the stream continues without interruption. New columns are silently
# ignored and NOT captured anywhere -- not as real columns, not in
# `_rescued_data` -- unless `rescuedDataColumn` is explicitly enabled (it
# isn't here). Existing columns are unaffected.
#
# Error/recovery workflow: none exists, because nothing fails -- which is
# exactly the danger. Data loss is real and silent: a new field simply never
# reaches this table, with no error, no log entry calling it out, nothing to
# "recover" from because nothing looks wrong. Only appropriate when you are
# confident the source schema is genuinely fixed and any future new column
# is deliberately unneeded -- otherwise this is the mode most likely to hide
# a real problem.
#
# schemaLocation is intentionally NOT set: the pipeline manages it
# automatically.
from pyspark import pipelines as dp

catalog = spark.conf.get("clickstream_catalog")
LANDING_PATH = f"/Volumes/{catalog}/bronze_clickstream/s3_clickstream_raw/web_events/landing"


@dp.table()
def web_events_none():
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaEvolutionMode", "none")
        .load(LANDING_PATH)
    )
