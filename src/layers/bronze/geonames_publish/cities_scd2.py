# SCD Type 2 modeling of GeoNames' cities500 dataset -- see
# country_info_scd2.py for why `source` points at a temp view wrapping the
# raw table directly, and for the timestamp/SCD2-only reasoning.
#
# Keyed by geonameid -- confirmed unique (235,878 distinct of 235,878 rows)
# via the real source data before this was written.
from pyspark import pipelines as dp
from pyspark.sql.functions import current_timestamp


@dp.temporary_view()
def cities_transformed():
    return spark.read.table("bronze_geonames.cities_raw").withColumn(
        "transformed_timestamp", current_timestamp()
    )


dp.create_streaming_table(name="cities_scd2")
dp.create_auto_cdc_from_snapshot_flow(
    target="cities_scd2",
    source="cities_transformed",
    keys=["geonameid"],
    stored_as_scd_type=2,
    track_history_except_column_list=["ingested_timestamp", "transformed_timestamp"],
)
