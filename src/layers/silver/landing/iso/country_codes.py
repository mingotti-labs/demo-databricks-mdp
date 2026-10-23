# SCD2 is the only variant Bronze Publish has for country_codes (SCD1 dropped from
# phase3i's scope -- see bronze_iso_publish's design.md). Reads only the rows
# Auto CDC inserted or closed in the SCD2 table (its change data feed) and
# applies them by version key, so the run-time stamp lands only on changed rows
# (openspec rollout-bronze-full-pattern).
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.silver_landing import land_changes  # noqa: E402


@dp.temporary_view()
def country_codes_changes():
    return land_changes(
        spark, "bronze_iso_publish.country_codes_scd2", ["country_code_alpha2"], "iso"
    )


dp.create_streaming_table(name="silver_landing_iso.country_codes")
dp.create_auto_cdc_flow(
    target="silver_landing_iso.country_codes",
    source="country_codes_changes",
    keys=["country_code_alpha2", "scd_valid_from_timestamp"],
    sequence_by="_commit_version",
    except_column_list=["_commit_version"],
    stored_as_scd_type=1,
)
