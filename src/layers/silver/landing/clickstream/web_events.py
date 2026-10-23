# SCD1 is the only variant Bronze Publish has for web_events (mechanical
# passthrough -- each event_id only ever appears once). Python variant is
# canonical over the SQL one. Reads only the rows Auto CDC changed (its change
# data feed) and applies them by key, so the run-time stamp lands only on
# changed rows (openspec refactor-airroi-clickstream-neon).
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.silver_landing import land_changes  # noqa: E402


@dp.temporary_view()
def web_events_changes():
    return land_changes(
        spark,
        "bronze_clickstream_publish.web_events_scd1",
        ["event_id"],
        "clickstream",
        scd2=False,
    )


dp.create_streaming_table(name="silver_landing_clickstream.web_events")
dp.create_auto_cdc_flow(
    target="silver_landing_clickstream.web_events",
    source="web_events_changes",
    keys=["event_id"],
    sequence_by="_commit_version",
    except_column_list=["_commit_version"],
    stored_as_scd_type=1,
)
