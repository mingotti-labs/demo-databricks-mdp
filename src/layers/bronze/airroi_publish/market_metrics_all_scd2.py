# SCD Type 2 modeling of AirROI's market metrics time series -- SCD2 only,
# matching market_summary_scd2's scope decision.
#
# Keyed by market (_country/_region/_locality/_district) + `date`: each
# (market, date) pair is a distinct data point (e.g. Urubici's Dec 2025
# forecast), and AirROI can revise a given month's forecast on a later
# pull as it approaches -- SCD2 keeps that revision history instead of
# silently overwriting it, which is the actual reason this needs SCD2
# rather than a plain append-only landing (unlike market_summary, where
# the SCD2 need was about tracking a single evolving "current value" per
# market; here it's about tracking how each future month's forecast
# itself changes call to call).
#
# transformed_timestamp / ingested_timestamp handling matches
# market_summary_scd2.py -- see that file's header for why both are
# excluded from track_history_except_column_list.
from pyspark import pipelines as dp
from pyspark.sql.functions import current_timestamp


@dp.temporary_view()
def market_metrics_all_transformed():
    return spark.read.table("bronze_airroi.market_metrics_all_raw").withColumn(
        "transformed_timestamp", current_timestamp()
    )


dp.create_streaming_table(name="market_metrics_all_scd2")
dp.create_auto_cdc_from_snapshot_flow(
    target="market_metrics_all_scd2",
    source="market_metrics_all_transformed",
    keys=["_country", "_region", "_locality", "_district", "date"],
    stored_as_scd_type=2,
    track_history_except_column_list=["ingested_timestamp", "transformed_timestamp"],
)
