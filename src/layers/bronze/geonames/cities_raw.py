# Full-refresh batch pull of GeoNames' cities500 dataset -- all populated
# places with population > 500, the smallest of GeoNames' official
# population-filtered variants (confirmed via a real fetch: 235,878 rows,
# ~14MB compressed / ~41MB uncompressed). An order of magnitude larger than
# UNGM's ~1.4MB fetch but still well within a single-shot driver-side
# fetch -- no custom Spark DataSource or partitioned reader needed, since
# this is a flat file, not a paginated API.
#
# Table name is `cities_raw`, not `cities500_raw` -- the population
# threshold is a source-selection detail (recorded in the table comment),
# not part of the entity's identity, matching unspsc_public_raw not
# encoding UNGM's pagination scheme in its name.
import sys

from pyspark import pipelines as dp
from pyspark.sql.functions import current_timestamp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.geonames import fetch_geonames_zip_dump  # noqa: E402

CITIES_URL = spark.conf.get("geonames_cities_url")

# cities500.txt has no header row -- fieldnames are GeoNames' documented
# 19-column "geoname" table shape (download.geonames.org/export/dump/readme.txt).
FIELDNAMES = [
    "geonameid",
    "name",
    "asciiname",
    "alternatenames",
    "latitude",
    "longitude",
    "feature_class",
    "feature_code",
    "country_code",
    "cc2",
    "admin1_code",
    "admin2_code",
    "admin3_code",
    "admin4_code",
    "population",
    "elevation",
    "dem",
    "timezone",
    "modification_date",
]

ATTRIBUTION = "This site or product includes GeoNames geographical data (cities500, population > 500), https://www.geonames.org, licensed under CC BY 4.0."


@dp.materialized_view(comment=ATTRIBUTION)
def cities_raw():
    records = fetch_geonames_zip_dump(CITIES_URL, "cities500.txt", FIELDNAMES)
    return spark.createDataFrame(records).withColumn("ingested_timestamp", current_timestamp())
