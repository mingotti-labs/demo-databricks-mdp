# SCD2 is the only variant Bronze Publish has for subdivision_codes (SCD1 dropped from
# phase3i's scope -- see bronze_iso_publish's design.md). Reads only the rows
# Auto CDC inserted or closed in the SCD2 table (its change data feed) and
# applies them by version key, so the run-time stamp lands only on changed rows
# (openspec rollout-bronze-full-pattern).
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.silver_landing import land_changes  # noqa: E402

NATURAL_KEYS = ["subdivision_code", "language_code", "subdivision_name"]


@dp.temporary_view()
def subdivision_codes_changes():
    return land_changes(
        spark, "bronze_iso_publish.subdivision_codes_scd2", NATURAL_KEYS, "iso"
    )


dp.create_streaming_table(name="silver_landing_iso.subdivision_codes")
dp.create_auto_cdc_flow(
    target="silver_landing_iso.subdivision_codes",
    source="subdivision_codes_changes",
    keys=[*NATURAL_KEYS, "scd_valid_from_timestamp"],
    sequence_by="_commit_version",
    except_column_list=["_commit_version"],
    stored_as_scd_type=1,
)
