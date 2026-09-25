# SCD Type 2 modeling of GeoNames' admin2 (county-level) codes -- see
# country_info_scd2.py for why `source` points at a temp view wrapping the
# raw table directly, and for the timestamp/SCD2-only reasoning.
#
# Keyed by code -- confirmed unique (47,643 distinct of 47,643 rows) via
# the real source data before this was written.
from pyspark import pipelines as dp
from pyspark.sql.functions import current_timestamp


@dp.temporary_view()
def admin2_codes_transformed():
    return spark.read.table("bronze_geonames.admin2_codes_raw").withColumn(
        "transformed_timestamp", current_timestamp()
    )


dp.create_streaming_table(name="admin2_codes_scd2")
dp.create_auto_cdc_from_snapshot_flow(
    target="admin2_codes_scd2",
    source="admin2_codes_transformed",
    keys=["code"],
    stored_as_scd_type=2,
    track_history_except_column_list=["ingested_timestamp", "transformed_timestamp"],
)
