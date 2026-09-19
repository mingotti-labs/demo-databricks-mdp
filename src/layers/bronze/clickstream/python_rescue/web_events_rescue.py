# Auto Loader schema evolution -- rescue.
#
# Behavior (Databricks docs -- not independently re-verified via a live run
# here, per direct instruction: only addNewColumns was exercised for real):
# the stream never fails due to schema changes; processing continues
# uninterrupted. Auto Loader never evolves the schema -- new columns are
# recorded as JSON inside the `_rescued_data` column instead of becoming real
# typed columns.
#
# Error/recovery workflow: none required. There's no failure to recover from
# -- new fields simply accumulate inside `_rescued_data` (a JSON string) for
# as long as this mode runs. To actually use a rescued field, a human
# inspects `_rescued_data` at their own convenience (e.g.
# `SELECT get_json_object(_rescued_data, '$.device_type') FROM web_events_rescue`)
# and decides whether it's worth promoting to a real column -- which means
# switching this pipeline to addNewColumns (or manually adding the column),
# not something this mode does on its own. Best suited when schema stability
# matters more than capturing every new field as a typed column immediately.
#
# schemaLocation is intentionally NOT set: the pipeline manages it
# automatically.
from pyspark import pipelines as dp

catalog = spark.conf.get("clickstream_catalog")
LANDING_PATH = f"/Volumes/{catalog}/bronze_clickstream/s3_clickstream_raw/web_events/landing"


@dp.table()
def web_events_rescue():
    return (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaEvolutionMode", "rescue")
        .load(LANDING_PATH)
    )
