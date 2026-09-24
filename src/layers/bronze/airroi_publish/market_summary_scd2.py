# SCD Type 2 modeling of AirROI's market summary data -- SCD2 only, no
# SCD1 (a deliberate scope decision: SCD1 would just duplicate SCD2's
# `WHERE __END_AT IS NULL` filter for "current value").
#
# Keyed by the flat _country/_region/_locality/_district columns
# market_summary_raw carries, not the API's own nested `market` map --
# Auto CDC's `keys=` needs flat columns, not a struct/map type. _district
# is included so Cumuruxatiba (locality="Prado", district="Cumuruxatiba")
# doesn't collide with a hypothetical future Prado-level market -- it's
# NULL for the other three markets, which is fine as a key component.
#
# transformed_timestamp is stamped here (publish layer), separate from
# ingested_timestamp which market_summary_raw stamps (bronze layer) --
# the platform's two standard lineage timestamps, one per layer. Both are
# excluded via track_history_except_column_list: since current_timestamp()
# differs on every single run, leaving them untracked would make Auto CDC
# think every row changed every run, creating a spurious new SCD2 version
# each time regardless of whether the real data changed.
from pyspark import pipelines as dp
from pyspark.sql.functions import current_timestamp


@dp.temporary_view()
def market_summary_transformed():
    return spark.read.table("bronze_airroi.market_summary_raw").withColumn(
        "transformed_timestamp", current_timestamp()
    )


dp.create_streaming_table(name="market_summary_scd2")
dp.create_auto_cdc_from_snapshot_flow(
    target="market_summary_scd2",
    source="market_summary_transformed",
    keys=["_country", "_region", "_locality", "_district"],
    stored_as_scd_type=2,
    track_history_except_column_list=["ingested_timestamp", "transformed_timestamp"],
)
