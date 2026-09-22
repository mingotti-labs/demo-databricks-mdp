# Full-refresh batch pull of the ACNC Charity Register via a custom CKAN
# Spark data source, generic over any CKAN portal's `datastore_search` REST
# API (not hardcoded to ACNC's fields) -- schema inferred live from the
# resource's own field metadata, reads split into offset-range partitions.
# The source has no incremental cursor -- data.gov.au republishes the
# complete current register weekly -- so a Materialized View that re-fetches
# on each run is the correct dataset type, not a Streaming Table. row_limit
# is empty/unset for prd (full ~66k rows) and capped at 500 for dev/tst --
# ACNC has no separate sandbox dataset to isolate lower environments against
# the way UNGM's test endpoint did.
#
# The connector classes are defined inline here, not imported from
# src/common -- confirmed via a real ModuleNotFoundError that custom Spark
# data source classes are cloudpickled for execution in a separate worker
# process that does not inherit this pipeline's sys.path fix (the same fix
# unspsc_public_raw.py uses for its own, purely driver-side import). This is
# a known PySpark/Databricks limitation, not specific to this connector --
# confirmed against Databricks Community reports of the identical failure.
# A future second CKAN dataset would copy this file's connector block
# rather than import it.
import requests
from pyspark import pipelines as dp
from pyspark.sql.datasource import DataSource, DataSourceReader, InputPartition
from pyspark.sql.types import (
    BooleanType,
    DoubleType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

# CKAN's WAF blocks requests' default User-Agent string with a 403 -- same
# class of block confirmed for UNGM's API (see common/ungm.py); confirmed
# for data.gov.au via a real request before this connector was written.
USER_AGENT = "curl/8.0"

_CKAN_TYPE_MAP = {
    "text": StringType(),
    "int": LongType(),
    "int4": LongType(),
    "int8": LongType(),
    "float": DoubleType(),
    "numeric": DoubleType(),
    "timestamp": TimestampType(),
    "bool": BooleanType(),
}


def _datastore_search(base_url: str, resource_id: str, limit: int, offset: int = 0) -> dict:
    response = requests.get(
        f"{base_url}/data/api/3/action/datastore_search",
        params={"resource_id": resource_id, "limit": limit, "offset": offset},
        headers={"User-Agent": USER_AGENT},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["result"]


class CkanDataSourceReader(DataSourceReader):
    def __init__(self, schema: StructType, options: dict):
        self.schema = schema
        self.base_url = options["base_url"]
        self.resource_id = options["resource_id"]
        self.page_size = int(options.get("page_size", 1000))
        row_limit = options.get("row_limit")
        self.row_limit = int(row_limit) if row_limit else None

    def partitions(self):
        total = _datastore_search(self.base_url, self.resource_id, limit=1)["total"]
        if self.row_limit is not None:
            total = min(total, self.row_limit)
        return [
            InputPartition((offset, min(self.page_size, total - offset)))
            for offset in range(0, total, self.page_size)
        ]

    def read(self, partition):
        offset, limit = partition.value
        records = _datastore_search(self.base_url, self.resource_id, limit=limit, offset=offset)["records"]
        field_names = [f.name for f in self.schema.fields]
        for record in records:
            yield tuple(record.get(name) for name in field_names)


class CkanDataSource(DataSource):
    @classmethod
    def name(cls):
        return "ckan"

    def schema(self):
        fields = _datastore_search(self.options["base_url"], self.options["resource_id"], limit=1)["fields"]
        return StructType(
            [
                StructField(field["id"], _CKAN_TYPE_MAP.get(field["type"], StringType()))
                for field in fields
                if field["id"] != "_id"  # CKAN's own internal row id, not a real dataset field
            ]
        )

    def reader(self, schema: StructType):
        return CkanDataSourceReader(schema, self.options)


spark.dataSource.register(CkanDataSource)


@dp.materialized_view()
def charity_register_raw():
    return (
        spark.read.format("ckan")
        .option("base_url", spark.conf.get("acnc_base_url"))
        .option("resource_id", spark.conf.get("acnc_resource_id"))
        .option("row_limit", spark.conf.get("acnc_row_limit"))
        .load()
    )
