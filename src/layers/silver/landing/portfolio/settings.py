# Reads only the rows Auto CDC inserted or closed in each SCD2 table (its change
# data feed) and applies them by version key, so the run-time stamp lands only on
# changed rows (openspec rollout-bronze-full-pattern).
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.silver_landing import land_changes  # noqa: E402

KEYS = {
    "concept_mapping": ["figure", "taxonomy", "concept"],
    "predecessor_ciks": ["cik"],
    "settings": ["setting"],
    "risk_levels": ["level"],
    "target_mix": ["level"],
    "benchmarks": ["symbol"],
}


def define_landing(dataset: str, keys: list[str]) -> None:
    @dp.temporary_view(name=f"{dataset}_changes")
    def changes():
        return land_changes(spark, f"bronze_portfolio_publish.{dataset}_scd2", keys, "portfolio")

    dp.create_streaming_table(name=f"silver_landing.portfolio__{dataset}")
    dp.create_auto_cdc_flow(
        target=f"silver_landing.portfolio__{dataset}",
        source=f"{dataset}_changes",
        keys=[*keys, "scd_valid_from_timestamp"],
        sequence_by="_commit_version",
        except_column_list=["_commit_version"],
        stored_as_scd_type=1,
    )


for dataset, keys in KEYS.items():
    define_landing(dataset, keys)
