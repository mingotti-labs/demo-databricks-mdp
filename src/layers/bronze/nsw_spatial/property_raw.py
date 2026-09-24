# Full-refresh batch pull of NSW Spatial Services' "Property" layer via a
# custom Esri ArcGIS REST FeatureServer data source, generic over any
# FeatureServer layer (not hardcoded to this one) -- schema inferred live
# from the layer's own `?f=json` metadata, reads split into offset-range
# partitions via resultOffset/resultRecordCount (ArcGIS REST's equivalent
# of CKAN's offset/limit). The source has no incremental cursor -- every
# pull is the current full state -- so a Materialized View that re-fetches
# on each run is the correct dataset type, not a Streaming Table.
# row_limit is empty/unset for prd (full ~4.2M rows) and capped at 500 for
# dev/tst -- this FeatureServer has no separate sandbox layer to isolate
# lower environments against, same reasoning as ACNC's acnc_row_limit.
#
# Connector classes are defined inline here, not imported from src/common
# -- applying ACNC's real ModuleNotFoundError finding proactively: custom
# Spark data source classes are cloudpickled for execution in a separate
# worker process that does not inherit this pipeline's sys.path. A future
# second ArcGIS FeatureServer source (e.g. the sibling "Lot" layer) would
# copy this file's connector block rather than import it.
from datetime import datetime, timezone

import requests
from pyspark import pipelines as dp
from pyspark.sql.datasource import DataSource, DataSourceReader, InputPartition
from pyspark.sql.types import (
    DoubleType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

# Same class of WAF block confirmed for UNGM's and ACNC's APIs -- applied
# proactively here rather than discovered via a failed run.
USER_AGENT = "curl/8.0"

_ESRI_TYPE_MAP = {
    "esriFieldTypeOID": LongType(),
    "esriFieldTypeInteger": LongType(),
    "esriFieldTypeSmallInteger": LongType(),
    "esriFieldTypeDouble": DoubleType(),
    "esriFieldTypeSingle": DoubleType(),
    "esriFieldTypeString": StringType(),
    "esriFieldTypeDate": TimestampType(),
}

_EXCLUDED_FIELDS = {"OBJECTID"}  # ArcGIS's own internal row id, not a real layer field


def _layer_metadata(service_url: str, layer_id: str) -> dict:
    response = requests.get(
        f"{service_url}/{layer_id}",
        params={"f": "json"},
        headers={"User-Agent": USER_AGENT},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def _layer_query(service_url: str, layer_id: str, **params) -> dict:
    response = requests.get(
        f"{service_url}/{layer_id}/query",
        params={"f": "json", "returnGeometry": "false", **params},
        headers={"User-Agent": USER_AGENT},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


class ArcGisFeatureServerDataSourceReader(DataSourceReader):
    def __init__(self, schema: StructType, options: dict):
        self.schema = schema
        self.service_url = options["service_url"]
        self.layer_id = options["layer_id"]
        self.requested_page_size = int(options.get("page_size", 1000))
        row_limit = options.get("row_limit")
        self.row_limit = int(row_limit) if row_limit else None

    def partitions(self):
        # Every ArcGIS FeatureServer caps resultRecordCount at its own
        # maxRecordCount -- confirmed via a real run that this server caps
        # at 100, silently truncating a larger request instead of erroring.
        # A page_size above that cap produces fewer rows per partition than
        # planned, undercounting the total pull. Discover the real cap
        # rather than assume one.
        metadata = _layer_metadata(self.service_url, self.layer_id)
        self.page_size = min(self.requested_page_size, metadata["maxRecordCount"])

        count_result = _layer_query(
            self.service_url, self.layer_id, where="1=1", returnCountOnly="true"
        )
        total = count_result["count"]
        if self.row_limit is not None:
            total = min(total, self.row_limit)
        return [
            InputPartition((offset, min(self.page_size, total - offset)))
            for offset in range(0, total, self.page_size)
        ]

    def read(self, partition):
        offset, limit = partition.value
        field_names = [f.name for f in self.schema.fields]
        result = _layer_query(
            self.service_url,
            self.layer_id,
            where="1=1",
            outFields=",".join(field_names),
            resultOffset=offset,
            resultRecordCount=limit,
        )
        for feature in result["features"]:
            attrs = feature["attributes"]
            row = []
            for field in self.schema.fields:
                value = attrs.get(field.name)
                if isinstance(field.dataType, TimestampType) and value is not None:
                    value = datetime.fromtimestamp(value / 1000, tz=timezone.utc)
                row.append(value)
            yield tuple(row)


class ArcGisFeatureServerDataSource(DataSource):
    @classmethod
    def name(cls):
        return "arcgis_feature_server"

    def schema(self):
        metadata = _layer_metadata(self.options["service_url"], self.options["layer_id"])
        return StructType(
            [
                StructField(field["name"], _ESRI_TYPE_MAP.get(field["type"], StringType()))
                for field in metadata["fields"]
                if field["name"] not in _EXCLUDED_FIELDS
            ]
        )

    def reader(self, schema: StructType):
        return ArcGisFeatureServerDataSourceReader(schema, self.options)


spark.dataSource.register(ArcGisFeatureServerDataSource)


@dp.materialized_view()
def property_raw():
    return (
        spark.read.format("arcgis_feature_server")
        .option("service_url", spark.conf.get("nsw_property_service_url"))
        .option("layer_id", spark.conf.get("nsw_property_layer_id"))
        .option("row_limit", spark.conf.get("nsw_property_row_limit"))
        .load()
    )
