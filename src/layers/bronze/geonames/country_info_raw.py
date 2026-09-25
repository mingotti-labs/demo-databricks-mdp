# Full-refresh batch pull of GeoNames' country reference data -- the
# source is a single static tab-delimited file with no pagination and no
# incremental cursor (confirmed via a real fetch before this was written:
# 252 rows -- more than ISO 3166-1's 249, since GeoNames includes some
# non-ISO entities such as disputed/dependent territories), so a
# Materialized View that re-fetches the whole file each run is correct.
import sys

from pyspark import pipelines as dp
from pyspark.sql.functions import current_timestamp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.geonames import fetch_geonames_dump  # noqa: E402

COUNTRY_INFO_URL = spark.conf.get("geonames_country_info_url")

# No header row DictReader can use -- countryInfo.txt's real header is one
# of several `#`-prefixed documentation lines, not reliably the first or
# last, so fieldnames are supplied explicitly (see common/geonames.py).
FIELDNAMES = [
    "iso_alpha2",
    "iso_alpha3",
    "iso_numeric",
    "fips",
    "country",
    "capital",
    "area",
    "population",
    "continent",
    "tld",
    "currency_code",
    "currency_name",
    "phone",
    "postal_code_format",
    "postal_code_regex",
    "languages",
    "geonameid",
    "neighbours",
    "equivalent_fips_code",
]

# Required by GeoNames' CC BY 4.0 license -- recorded as a Unity Catalog
# table comment, not just in repo docs, same as ISO's attribution.
ATTRIBUTION = "This site or product includes GeoNames geographical data, https://www.geonames.org, licensed under CC BY 4.0."


@dp.materialized_view(comment=ATTRIBUTION)
def country_info_raw():
    records = fetch_geonames_dump(COUNTRY_INFO_URL, FIELDNAMES)
    return spark.createDataFrame(records).withColumn("ingested_timestamp", current_timestamp())
