# SCD2 selected over SCD1 per silver.md's precedence rule (SCD2 > SCD1 > SCD0).
# Reads only the rows Auto CDC inserted or closed in the bronze SCD2 table (its
# change data feed) and applies them by version key, so the run-time stamp lands
# only on changed rows (openspec rollout-bronze-full-pattern). The view is named
# property_changes; the target's name is the table, `property`.
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.silver_landing import land_changes  # noqa: E402


@dp.temporary_view()
def property_changes():
    return land_changes(
        spark,
        "bronze_nsw_spatial_publish.property_scd2",
        ["addressstringoid"],
        "nsw_spatial",
    )


dp.create_streaming_table(name="silver_landing_nsw_spatial.property")
dp.create_auto_cdc_flow(
    target="silver_landing_nsw_spatial.property",
    source="property_changes",
    keys=["addressstringoid", "scd_valid_from_timestamp"],
    sequence_by="_commit_version",
    except_column_list=["_commit_version"],
    stored_as_scd_type=1,
)
