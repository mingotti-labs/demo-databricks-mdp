# SCD Type 2 (full history, __START_AT/__END_AT) modeling of the ISO 10383
# market identifier codes, the bronze full pattern as for country_codes_scd2:
# raw's ingested_timestamp is left out of the snapshot, Auto CDC versions each
# snapshot with the pipeline update's time, and Silver Landing reads the change
# feed. Keyed by market_identifier_code -- unique in all 2,889 rows (probe P1).
from pyspark import pipelines as dp


@dp.temporary_view()
def market_identifier_codes_snapshot():
    return spark.read.table("bronze_iso.market_identifier_codes_raw").drop("ingested_timestamp")


dp.create_streaming_table(
    name="bronze_iso_publish.market_identifier_codes_scd2",
    table_properties={
        "pipelines.reset.allowed": "false",
        "delta.enableChangeDataFeed": "true",
    },
)
dp.create_auto_cdc_from_snapshot_flow(
    target="bronze_iso_publish.market_identifier_codes_scd2",
    source="market_identifier_codes_snapshot",
    keys=["market_identifier_code"],
    stored_as_scd_type=2,
)
