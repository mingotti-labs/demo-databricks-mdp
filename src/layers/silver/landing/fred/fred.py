# Reads only the rows Auto CDC changed in the FRED Bronze Publish table (its change
# data feed) and applies them by key, so the run-time stamp lands only on changed
# rows (openspec rollout-bronze-full-pattern). Bronze keeps FRED's dates as text
# (`2026-10-29`); Landing turns observation_date into a date. A value that does not
# read as a date fails the update (ANSI) instead of becoming null.
import sys

from pyspark import pipelines as dp
from pyspark.sql import functions as F

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.silver_landing import land_changes  # noqa: E402

KEYS = ["series_id", "observation_date"]


@dp.temporary_view(name="observations_changes")
def observations_changes():
    changes = land_changes(
        spark, "bronze_fred_publish.observations_scd1", KEYS, "fred", False
    )
    changes = changes.withColumn("observation_date", F.to_date("observation_date"))
    return changes.withMetadata("observation_date", {"comment": "Natural key"})


dp.create_streaming_table(name="silver_landing.fred__observations")
dp.create_auto_cdc_flow(
    target="silver_landing.fred__observations",
    source="observations_changes",
    keys=KEYS,
    sequence_by="_commit_version",
    except_column_list=["_commit_version"],
    stored_as_scd_type=1,
)
