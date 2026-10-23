# SCD Type 2 modeling of GeoNames' admin2 (county-level) codes -- see
# country_info_scd2.py for why `source` points at a temp view wrapping the
# raw table directly, and for the timestamp/SCD2-only reasoning.
#
# Keyed by code -- confirmed unique (47,643 distinct of 47,643 rows) via
# the real source data before this was written.
# Bronze full pattern (openspec rollout-bronze-full-pattern): raw stamps
# ingested_timestamp on every row at every load, so it is left out of the
# snapshot; with it in, Auto CDC would rewrite every current row each run. Auto
# CDC versions each snapshot with the pipeline update's time (__START_AT,
# __END_AT), and Silver Landing reads the change feed (enabled below).
from pyspark import pipelines as dp


@dp.temporary_view()
def admin2_codes_snapshot():
    return spark.read.table("bronze_geonames.admin2_codes_raw").drop("ingested_timestamp")


dp.create_streaming_table(
    name="bronze_geonames_publish.admin2_codes_scd2",
    table_properties={
        "pipelines.reset.allowed": "false",
        "delta.enableChangeDataFeed": "true",
    },
)
dp.create_auto_cdc_from_snapshot_flow(
    target="bronze_geonames_publish.admin2_codes_scd2",
    source="admin2_codes_snapshot",
    keys=["code"],
    stored_as_scd_type=2,
)
