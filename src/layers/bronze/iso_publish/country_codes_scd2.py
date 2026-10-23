# SCD Type 2 (full history, __START_AT/__END_AT) modeling of ISO 3166-1
# country codes. `source` points at country_codes_snapshot, a private
# temp view over bronze_iso.country_codes_raw -- no intermediate
# snapshot materialized view (see phase3b-scd-snapshot-cleanup's
# design.md: that wrapper was tried, found unnecessary, and removed
# project-wide), just the column drop below.
#
# Keyed by country_code_alpha2 -- confirmed unique (249 distinct of 249
# rows) via the real source data.
#
# SCD2-only for this table (and subdivision_codes) -- SCD1 dropped from
# this change's scope; low-change-frequency reference data doesn't need a
# separate "latest value" table when SCD2's `WHERE __END_AT IS NULL` gives
# the same thing.
#
# Bronze full pattern (openspec rollout-bronze-full-pattern): raw stamps
# ingested_timestamp on every row at every load, so it is left out of the
# snapshot; with it in, Auto CDC would rewrite every current row each run.
# Auto CDC versions each snapshot with the pipeline update's time (__START_AT,
# __END_AT), and Silver Landing reads the change feed (enabled below).
from pyspark import pipelines as dp


@dp.temporary_view()
def country_codes_snapshot():
    return spark.read.table("bronze_iso.country_codes_raw").drop("ingested_timestamp")


dp.create_streaming_table(
    name="bronze_iso_publish.country_codes_scd2",
    table_properties={
        "pipelines.reset.allowed": "false",
        "delta.enableChangeDataFeed": "true",
    },
)
dp.create_auto_cdc_from_snapshot_flow(
    target="bronze_iso_publish.country_codes_scd2",
    source="country_codes_snapshot",
    keys=["country_code_alpha2"],
    stored_as_scd_type=2,
)
