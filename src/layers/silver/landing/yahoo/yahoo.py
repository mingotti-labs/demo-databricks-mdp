# Reads only the rows Auto CDC changed in each Yahoo Bronze Publish table (its
# change data feed) and applies them by key, so the run-time stamp lands only on
# changed rows (openspec rollout-bronze-full-pattern). The calendar is SCD2, so its
# Landing key also carries the version start.
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.silver_landing import land_changes  # noqa: E402

TABLES = {
    "prices": (["symbol", "date"], False),
    "events": (["symbol", "date", "event_type"], False),
    "options": (["symbol"], False),
    "calendar": (["symbol"], True),
}


def landing(table: str, keys: list[str], scd2: bool) -> None:
    suffix = "scd2" if scd2 else "scd1"

    @dp.temporary_view(name=f"{table}_changes")
    def changes():
        return land_changes(spark, f"bronze_yahoo_publish.{table}_{suffix}", keys, "yahoo", scd2)

    dp.create_streaming_table(name=f"silver_landing_yahoo.{table}")
    dp.create_auto_cdc_flow(
        target=f"silver_landing_yahoo.{table}",
        source=f"{table}_changes",
        keys=keys + ["scd_valid_from_timestamp"] if scd2 else keys,
        sequence_by="_commit_version",
        except_column_list=["_commit_version"],
        stored_as_scd_type=1,
    )


for table, (keys, scd2) in TABLES.items():
    landing(table, keys, scd2)
