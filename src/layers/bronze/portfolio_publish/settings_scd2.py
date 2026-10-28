# SCD Type 2 modeling of each settings file, so every change to a setting is kept
# with its date. Bronze full pattern (openspec rollout-bronze-full-pattern): the
# raw tables stamp ingested_timestamp on every row at every load, so it is left
# out of the snapshot; Auto CDC versions each snapshot with the pipeline update's
# time (__START_AT, __END_AT) and Silver Landing reads the change feed.
from pyspark import pipelines as dp

KEYS = {
    "concept_mapping": ["figure", "taxonomy", "concept"],
    "predecessor_ciks": ["cik"],
    "settings": ["setting"],
    "risk_levels": ["level"],
    "target_mix": ["level"],
    "benchmarks": ["symbol"],
}


def define_scd2(dataset: str, keys: list[str]) -> None:
    @dp.temporary_view(name=f"{dataset}_snapshot")
    def snapshot():
        return spark.read.table(f"bronze_portfolio.{dataset}_raw").drop("ingested_timestamp")

    target = f"bronze_portfolio_publish.{dataset}_scd2"
    dp.create_streaming_table(
        name=target,
        table_properties={
            "pipelines.reset.allowed": "false",
            "delta.enableChangeDataFeed": "true",
        },
    )
    dp.create_auto_cdc_from_snapshot_flow(
        target=target,
        source=f"{dataset}_snapshot",
        keys=keys,
        stored_as_scd_type=2,
    )


for dataset, keys in KEYS.items():
    define_scd2(dataset, keys)
