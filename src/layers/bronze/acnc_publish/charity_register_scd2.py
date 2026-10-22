# SCD Type 2 modeling of the ACNC Charity Register: the bronze full pattern
# (bronze_publish_scd2_autocdc_full_load_python, openspec
# correct-platform-timestamps).
#
# charity_register_raw is a full load, so its ingested_timestamp changes on
# every row at every load. It is therefore never part of the snapshot: Auto
# CDC would rewrite every current row each run. It is used only as the
# snapshot's version (raw's fetch time), which Auto CDC writes as __START_AT on
# the versions it inserts and __END_AT on the ones it closes. Auto CDC keeps
# the version to the millisecond, so the fetch time is cut to the millisecond
# or raw would always look newer and the same snapshot would be applied forever.
from pyspark import pipelines as dp
from pyspark.sql import functions as F


def next_snapshot(latest_version):
    raw = spark.read.table("bronze_acnc.charity_register_raw")
    fetched = raw.agg(
        F.date_trunc("millisecond", F.max("ingested_timestamp"))
    ).first()[0]
    if latest_version is not None and fetched <= latest_version:
        return None
    return raw.where("ABN IS NOT NULL").drop("ingested_timestamp"), fetched


# pipelines.reset.allowed=false: a full refresh of the bronze pipeline is
# refused instead of truncating the history (openspec acnc-two-pipelines D6).
# Change data feed feeds Silver Landing.
dp.create_streaming_table(
    name="bronze_acnc_publish.charity_register_scd2",
    table_properties={
        "pipelines.reset.allowed": "false",
        "delta.enableChangeDataFeed": "true",
    },
)
dp.create_auto_cdc_from_snapshot_flow(
    target="bronze_acnc_publish.charity_register_scd2",
    source=next_snapshot,
    keys=["ABN"],
    stored_as_scd_type=2,
)
