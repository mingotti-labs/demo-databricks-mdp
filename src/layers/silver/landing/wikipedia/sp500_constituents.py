# Reads only the rows Auto CDC inserted or closed in the SCD2 table (its change
# data feed) and applies them by version key, so the run-time stamp lands only
# on changed rows (openspec rollout-bronze-full-pattern).
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.silver_landing import land_changes  # noqa: E402


@dp.temporary_view()
def sp500_constituents_changes():
    return land_changes(
        spark, "bronze_wikipedia_publish.sp500_constituents_scd2", ["symbol"], "wikipedia"
    )


dp.create_streaming_table(name="silver_landing.wikipedia__sp500_constituents")
dp.create_auto_cdc_flow(
    target="silver_landing.wikipedia__sp500_constituents",
    source="sp500_constituents_changes",
    keys=["symbol", "scd_valid_from_timestamp"],
    sequence_by="_commit_version",
    except_column_list=["_commit_version"],
    stored_as_scd_type=1,
)
