# Auto Loader schema evolution -- failOnNewColumns.
#
# Behavior (Databricks docs -- not independently re-verified via a live run
# here, per direct instruction: only addNewColumns was exercised for real):
# the stream fails immediately on a new column and does NOT restart
# automatically -- unlike addNewColumns, there is no self-healing retry.
# The schema is not updated automatically.
#
# Error/recovery workflow: genuinely manual. The pipeline update stays FAILED
# until a human either (a) updates the target table's schema explicitly to
# include the new column, or (b) removes/quarantines the offending source
# file so the stream no longer sees it, then re-triggers the pipeline. This
# mode enforces schema governance deliberately -- it's the right choice when
# an unannounced new column should block the pipeline rather than be silently
# absorbed, e.g. a contract with a regulated or billing-sensitive source.
#
# schemaLocation is intentionally NOT set: the pipeline manages it
# automatically.
from pyspark import pipelines as dp

catalog = spark.conf.get("clickstream_catalog")
LANDING_PATH = f"/Volumes/{catalog}/bronze_clickstream/s3_clickstream_raw/web_events/landing"


@dp.table()
def web_events_fail_on_new_columns():
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaEvolutionMode", "failOnNewColumns")
        .load(LANDING_PATH)
    )
