# SCD Type 2 (full history, __START_AT/__END_AT) modeling of ISO 3166-1
# country codes. `source` points at country_codes_transformed, a private
# temp view wrapping bronze_iso.country_codes_raw -- no intermediate
# snapshot materialized view (see phase3b-scd-snapshot-cleanup's
# design.md: that wrapper was tried, found unnecessary, and removed
# project-wide), just the timestamp stamp below.
#
# Keyed by country_code_alpha2 -- confirmed unique (249 distinct of 249
# rows) via the real source data.
#
# SCD2-only for this table (and subdivision_codes) -- SCD1 dropped from
# this change's scope; low-change-frequency reference data doesn't need a
# separate "latest value" table when SCD2's `WHERE __END_AT IS NULL` gives
# the same thing.
#
# transformed_timestamp is stamped here (publish layer), separate from
# ingested_timestamp which country_codes_raw stamps (bronze layer) -- the
# platform's two standard lineage timestamps, one per layer (see
# NAMING.md). Both are excluded via track_history_except_column_list:
# since current_timestamp() differs on every run, leaving them untracked
# would make Auto CDC think every row changed every run, creating a
# spurious new SCD2 version each time regardless of whether the real data
# changed. Same pattern as AirROI's market_summary_scd2.py.
from pyspark import pipelines as dp
from pyspark.sql.functions import current_timestamp


@dp.temporary_view()
def country_codes_transformed():
    return spark.read.table("bronze_iso.country_codes_raw").withColumn(
        "transformed_timestamp", current_timestamp()
    )


dp.create_streaming_table(name="country_codes_scd2")
dp.create_auto_cdc_from_snapshot_flow(
    target="country_codes_scd2",
    source="country_codes_transformed",
    keys=["country_code_alpha2"],
    stored_as_scd_type=2,
    track_history_except_column_list=["ingested_timestamp", "transformed_timestamp"],
)
