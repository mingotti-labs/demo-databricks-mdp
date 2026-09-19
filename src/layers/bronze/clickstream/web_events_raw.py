# Ingests clickstream event files via Auto Loader into a Streaming Table.
# schemaEvolutionMode is explicit (Auto Loader's own default, addNewColumns) so
# the setting is visible in source, not left implicit -- see this pipeline's
# OpenSpec design.md for why that distinction matters for this pattern.
# schemaLocation is intentionally NOT set: the pipeline manages it automatically.
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
