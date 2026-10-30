# Reads only the rows Auto CDC inserted or closed in each SEC SCD2 table (its
# change data feed) and applies them by version key, so the run-time stamp lands
# only on changed rows (openspec rollout-bronze-full-pattern).
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.silver_landing import land_changes  # noqa: E402

TABLES = {
    "company_tickers": ["cik", "ticker"],
    "company_facts": ["cik", "taxonomy", "concept", "unit", "accn", "start", "end"],
}


def landing(table: str, keys: list[str]) -> None:
    @dp.temporary_view(name=f"{table}_changes")
    def changes():
        return land_changes(spark, f"bronze_sec_publish.{table}_scd2", keys, "sec")

    dp.create_streaming_table(name=f"silver_landing.sec__{table}")
    dp.create_auto_cdc_flow(
        target=f"silver_landing.sec__{table}",
        source=f"{table}_changes",
        keys=keys + ["scd_valid_from_timestamp"],
        sequence_by="_commit_version",
        except_column_list=["_commit_version"],
        stored_as_scd_type=1,
    )


for table, keys in TABLES.items():
    landing(table, keys)
