# One Materialized View per curated settings file, read from the volume copy the
# run job's first task writes (src/common/copy_repo_files.py). Every column stays
# text exactly as the file shows it (no schema inference); silver casts. A
# Materialized View over the whole file is correct: each file is a full snapshot.
from pyspark import pipelines as dp
from pyspark.sql.functions import current_timestamp

VOLUME = spark.conf.get("portfolio_volume_root")
DATASETS = ["concept_mapping", "predecessor_ciks", "settings", "risk_levels", "target_mix"]


def read_dataset(dataset: str):
    return (
        spark.read.option("header", "true")
        .csv(f"{VOLUME}/{dataset}/landing/{dataset}.csv")
        .withColumn("ingested_timestamp", current_timestamp())
    )


def define_raw(dataset: str) -> None:
    @dp.materialized_view(name=f"{dataset}_raw")
    def raw():
        return read_dataset(dataset)


for dataset in DATASETS:
    define_raw(dataset)
