# SCD2 is the only variant Bronze Publish has for market_metrics_all (SCD1 would just
# duplicate SCD2's WHERE __END_AT IS NULL). Reads only the rows Auto CDC
# inserted or closed in the SCD2 table (its change data feed) and applies them
# by version key, so the run-time stamp lands only on changed rows (openspec
# rollout-bronze-full-pattern).
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.silver_landing import land_changes  # noqa: E402

NATURAL_KEYS = ["_country", "_region", "_locality", "_district", "date"]


@dp.temporary_view()
def market_metrics_all_changes():
    return land_changes(
        spark, "bronze_airroi_publish.market_metrics_all_scd2", NATURAL_KEYS, "airroi"
    )


dp.create_streaming_table(name="silver_landing.airroi__market_metrics_all")
dp.create_auto_cdc_flow(
    target="silver_landing.airroi__market_metrics_all",
    source="market_metrics_all_changes",
    keys=NATURAL_KEYS + ["scd_valid_from_timestamp"],
    sequence_by="_commit_version",
    except_column_list=["_commit_version"],
    stored_as_scd_type=1,
)
