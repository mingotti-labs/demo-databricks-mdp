# SCD Type 2 modeling of AirROI's market metrics time series -- SCD2 only, no SCD1 (a deliberate
# scope decision: SCD1 would just duplicate SCD2's `WHERE __END_AT IS NULL`).
#
# Keyed by the flat _country/_region/_locality/_district columns plus `date` (each (market, date) pair is a distinct data point, and AirROI can revise a month's forecast on a later pull) the raw
# table carries, not the API's nested `market` map (Auto CDC keys need flat
# columns). _district is NULL for three of the four markets, which is fine as a
# key component.
#
# Bronze full pattern (openspec rollout-bronze-full-pattern): raw stamps
# ingested_timestamp on every row at every load, so it is left out of the
# snapshot; with it in, Auto CDC would rewrite every current row each run. Auto
# CDC versions each snapshot with the pipeline update's time (__START_AT,
# __END_AT), and Silver Landing reads the change feed (enabled below).
from pyspark import pipelines as dp


@dp.temporary_view()
def market_metrics_all_snapshot():
    return spark.read.table("bronze_airroi.market_metrics_all_raw").drop("ingested_timestamp")


dp.create_streaming_table(
    name="bronze_airroi_publish.market_metrics_all_scd2",
    table_properties={
        "pipelines.reset.allowed": "false",
        "delta.enableChangeDataFeed": "true",
    },
)
dp.create_auto_cdc_from_snapshot_flow(
    target="bronze_airroi_publish.market_metrics_all_scd2",
    source="market_metrics_all_snapshot",
    keys=["_country", "_region", "_locality", "_district", "date"],
    stored_as_scd_type=2,
)
