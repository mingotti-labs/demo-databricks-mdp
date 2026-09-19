# Auto Loader schema evolution -- addNewColumns (this mode's default too).
#
# Behavior (Databricks docs): the stream halts with UnknownFieldException the
# moment a genuinely new column is seen; the triggering micro-batch's new data
# is not processed in that batch. New columns are merged into the schema;
# existing column types are unchanged.
#
# Error/recovery workflow -- CONFIRMED LIVE against this exact pipeline, not
# just read from docs (see phase3b-clickstream-autoloader's design.md): inside
# a Lakeflow Declarative Pipeline, this does not surface as a plain failure.
# The event log shows "Flow ... has encountered a schema change during
# execution and terminated. A new update using the new schema will be
# automatically started." The in-flight update is CANCELED (cause
# SCHEMA_CHANGE), and Databricks itself starts and completes a new update
# (also cause SCHEMA_CHANGE) with no human action needed. The one gotcha: the
# CLI/API call that observed the mid-flight cancellation (`bundle run`,
# `pipelines start-update`) exits/reports non-zero even though the pipeline
# recovers on its own -- don't mistake that for a real failure when scripting
# around this.
#
# schemaLocation is intentionally NOT set: the pipeline manages it
# automatically (setting it manually is an anti-pattern for SDP pipelines).
from pyspark import pipelines as dp

catalog = spark.conf.get("clickstream_catalog")
LANDING_PATH = f"/Volumes/{catalog}/bronze_clickstream/s3_clickstream_raw/web_events/landing"


@dp.table()
def web_events_raw():
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaEvolutionMode", "addNewColumns")
        .load(LANDING_PATH)
    )
