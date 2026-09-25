# Full-refresh batch pull of GeoNames' admin1 (state/province-level) codes
# -- same reasoning as country_info_raw.py (single static file, no
# pagination/cursor; confirmed via a real fetch: 3,865 rows).
import sys

from pyspark import pipelines as dp
from pyspark.sql.functions import current_timestamp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.geonames import fetch_geonames_dump  # noqa: E402

ADMIN1_URL = spark.conf.get("geonames_admin1_codes_url")

# admin1CodesASCII.txt has no header row at all (confirmed via a real
# fetch) -- fieldnames supplied explicitly.
FIELDNAMES = ["code", "name", "asciiname", "geonameid"]

ATTRIBUTION = "This site or product includes GeoNames geographical data, https://www.geonames.org, licensed under CC BY 4.0."


@dp.materialized_view(comment=ATTRIBUTION)
def admin1_codes_raw():
    records = fetch_geonames_dump(ADMIN1_URL, FIELDNAMES)
    return spark.createDataFrame(records).withColumn("ingested_timestamp", current_timestamp())
