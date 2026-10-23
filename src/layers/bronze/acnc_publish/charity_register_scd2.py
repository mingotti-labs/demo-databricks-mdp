# SCD Type 2 modeling of the ACNC Charity Register: the bronze full pattern
# (bronze_publish_scd2_autocdc_full_load_python, openspec
# correct-platform-timestamps).
#
# charity_register_raw is a full load, so its ingested_timestamp changes on
# every row at every load. It is left out of the snapshot: Auto CDC overwrites
# the current row for a column it does not track, so every row would be
# rewritten each run. Auto CDC then versions each snapshot with the pipeline
# update's time, written as __START_AT on the versions it inserts and __END_AT
# on the ones it closes. (A function source could pass raw's exact fetch time
# instead, but it cannot read a dataset defined in this same pipeline.)
from pyspark import pipelines as dp


@dp.temporary_view()
def charity_register_scd2_snapshot():
    return (
        spark.read.table("bronze_acnc.charity_register_raw")
        .where("ABN IS NOT NULL")
        .drop("ingested_timestamp")
    )


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
    source="charity_register_scd2_snapshot",
    keys=["ABN"],
    stored_as_scd_type=2,
)
