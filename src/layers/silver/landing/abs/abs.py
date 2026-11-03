# Reads only the rows Auto CDC changed in the ABS Bronze Publish table (its change
# data feed) and applies them by key, so the run-time stamp lands only on changed
# rows (openspec rollout-bronze-full-pattern). No type change: `time_period` is a
# quarter or a month (`1948-Q3`, `2024-04`), not a date, and `value` stays text.
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.silver_landing import land_changes  # noqa: E402

KEYS = ["series_key", "time_period"]


@dp.temporary_view(name="observations_changes")
def observations_changes():
    return land_changes(spark, "bronze_abs_publish.observations_scd1", KEYS, "abs", False)


dp.create_streaming_table(name="silver_landing.abs__observations")
dp.create_auto_cdc_flow(
    target="silver_landing.abs__observations",
    source="observations_changes",
    keys=KEYS,
    sequence_by="_commit_version",
    except_column_list=["_commit_version"],
    stored_as_scd_type=1,
)
