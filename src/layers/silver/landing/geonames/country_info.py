# SCD2 selected over SCD1 per silver.md's precedence rule (SCD2 > SCD1 > SCD0).
# Reads only the rows Auto CDC inserted or closed in the bronze SCD2 table (its
# change data feed) and applies them by version key, so the run-time stamp lands
# only on changed rows (openspec rollout-bronze-full-pattern).
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.silver_landing import land_changes  # noqa: E402


@dp.temporary_view()
def country_info_changes():
    return land_changes(
        spark, "bronze_geonames_publish.country_info_scd2", ["iso_alpha2"], "geonames"
    )


dp.create_streaming_table(name="silver_landing.geonames__country_info")
dp.create_auto_cdc_flow(
    target="silver_landing.geonames__country_info",
    source="country_info_changes",
    keys=["iso_alpha2", "scd_valid_from_timestamp"],
    sequence_by="_commit_version",
    except_column_list=["_commit_version"],
    stored_as_scd_type=1,
)
