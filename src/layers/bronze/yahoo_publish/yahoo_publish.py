# Bronze Publish for Yahoo by streaming Auto CDC from the append-only raw tables,
# sequenced by the fetch time. Each file holds only part of the data (new days,
# reloaded symbols), so there is no full snapshot to compare. Prices, events and
# options are SCD1 (user, 2026-10-29): raw keeps every fetch, so older values are
# never lost. The calendar is SCD2, so the history of announced pay dates is kept;
# its platform columns are left out of the target, so an unchanged calendar
# writes nothing and __START_AT is the fetch time of the version.
from pyspark import pipelines as dp

PLATFORM_COLUMNS = ["ingested_timestamp", "source_file_path", "_rescued_data"]
SCD1 = {
    "prices": ["symbol", "date"],
    "events": ["symbol", "date", "event_type"],
    "options": ["symbol"],
}


def define_scd1(dataset: str, keys: list[str]) -> None:
    target = f"bronze_yahoo_publish.{dataset}_scd1"
    dp.create_streaming_table(
        name=target,
        table_properties={"delta.enableChangeDataFeed": "true"},
        cluster_by_auto=dataset == "prices",
    )
    dp.create_auto_cdc_flow(
        target=target,
        source=f"bronze_yahoo.{dataset}_raw",
        keys=keys,
        sequence_by="ingested_timestamp",
        stored_as_scd_type=1,
    )


for dataset, keys in SCD1.items():
    define_scd1(dataset, keys)

dp.create_streaming_table(
    name="bronze_yahoo_publish.calendar_scd2",
    table_properties={"pipelines.reset.allowed": "false", "delta.enableChangeDataFeed": "true"},
)
dp.create_auto_cdc_flow(
    target="bronze_yahoo_publish.calendar_scd2",
    source="bronze_yahoo.calendar_raw",
    keys=["symbol"],
    sequence_by="ingested_timestamp",
    except_column_list=PLATFORM_COLUMNS,
    stored_as_scd_type=2,
)
