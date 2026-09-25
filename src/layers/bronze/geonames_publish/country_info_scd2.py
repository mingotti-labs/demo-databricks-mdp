# SCD Type 2 modeling of GeoNames' country reference data. `source` points
# at a private temp view wrapping bronze_geonames.country_info_raw
# directly -- no intermediate snapshot materialized view (see
# phase3b-scd-snapshot-cleanup's design.md: that wrapper was tried, found
# unnecessary, and removed project-wide), just the timestamp stamp below.
#
# Keyed by iso_alpha2 -- confirmed unique (252 distinct of 252 rows) via
# the real source data before this was written. Unlike ISO's
# subdivision_code, this key held up -- verified rather than assumed, same
# discipline either way.
#
# SCD2-only, no SCD1 -- same scope decision as
# phase3i-iso-country-reference-ingestion's, applied here from the start.
#
# transformed_timestamp stamped here (publish layer), separate from
# ingested_timestamp (bronze layer, country_info_raw.py). Both excluded
# via track_history_except_column_list -- same pattern as AirROI's/ISO's.
from pyspark import pipelines as dp
from pyspark.sql.functions import current_timestamp


@dp.temporary_view()
def country_info_transformed():
    return spark.read.table("bronze_geonames.country_info_raw").withColumn(
        "transformed_timestamp", current_timestamp()
    )


dp.create_streaming_table(name="country_info_scd2")
dp.create_auto_cdc_from_snapshot_flow(
    target="country_info_scd2",
    source="country_info_transformed",
    keys=["iso_alpha2"],
    stored_as_scd_type=2,
    track_history_except_column_list=["ingested_timestamp", "transformed_timestamp"],
)
