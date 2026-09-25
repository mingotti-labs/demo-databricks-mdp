# SCD1 is the only variant Bronze Publish has for web_events (mechanical
# passthrough -- each event_id only ever appears once). Python variant is
# canonical over the SQL one.
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.silver_landing import land  # noqa: E402


@dp.materialized_view()
def web_events():
    df = spark.read.table("bronze_clickstream_publish.web_events_scd1")
    return land(df, natural_keys=["event_id"], source_name="clickstream", scd2=False)
