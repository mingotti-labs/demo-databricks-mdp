# Reads only the rows Auto CDC changed in the RBA Bronze Publish table (its change
# data feed) and applies them by key, so the run-time stamp lands only on changed
# rows (openspec rollout-bronze-full-pattern). Bronze keeps the RBA's dates as text
# (`03-Jan-2023`); Landing turns observation_date and publication_date into dates.
# A value that does not read as a date fails the update (ANSI) instead of becoming null.
import sys

from pyspark import pipelines as dp
from pyspark.sql import functions as F

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.silver_landing import land_changes  # noqa: E402

KEYS = ["series_id", "observation_date"]
DATE_COLUMNS = ["observation_date", "publication_date"]
DATE_FORMAT = "dd-MMM-yyyy"


@dp.temporary_view(name="observations_changes")
def observations_changes():
    changes = land_changes(
        spark, "bronze_rba_publish.observations_scd1", KEYS, "rba", False
    )
    for column in DATE_COLUMNS:
        changes = changes.withColumn(column, F.to_date(column, DATE_FORMAT))
    return changes.withMetadata("observation_date", {"comment": "Natural key"})


dp.create_streaming_table(name="silver_landing.rba__observations")
dp.create_auto_cdc_flow(
    target="silver_landing.rba__observations",
    source="observations_changes",
    keys=KEYS,
    sequence_by="_commit_version",
    except_column_list=["_commit_version"],
    stored_as_scd_type=1,
)
