# SCD Type 2 modeling of GeoNames' country reference data. `source` points
# at a private temp view wrapping bronze_geonames.country_info_raw
# directly -- no intermediate snapshot materialized view (see
# phase3b-scd-snapshot-cleanup's design.md: that wrapper was tried, found
# unnecessary, and removed project-wide), just the column drop below.
#
# Keyed by iso_alpha2 -- confirmed unique (252 distinct of 252 rows) via
# the real source data before this was written. Unlike ISO's
# subdivision_code, this key held up -- verified rather than assumed, same
# discipline either way.
#
# SCD2-only, no SCD1 -- same scope decision as
# phase3i-iso-country-reference-ingestion's, applied here from the start.
#
# Bronze full pattern (openspec rollout-bronze-full-pattern): raw stamps
# ingested_timestamp on every row at every load, so it is left out of the
# snapshot; with it in, Auto CDC would rewrite every current row each run. Auto
# CDC versions each snapshot with the pipeline update's time (__START_AT,
# __END_AT), and Silver Landing reads the change feed (enabled below).
from pyspark import pipelines as dp


@dp.temporary_view()
def country_info_snapshot():
    return spark.read.table("bronze_geonames.country_info_raw").drop("ingested_timestamp")


dp.create_streaming_table(
    name="bronze_geonames_publish.country_info_scd2",
    table_properties={
        "pipelines.reset.allowed": "false",
        "delta.enableChangeDataFeed": "true",
    },
)
dp.create_auto_cdc_from_snapshot_flow(
    target="bronze_geonames_publish.country_info_scd2",
    source="country_info_snapshot",
    keys=["iso_alpha2"],
    stored_as_scd_type=2,
)
