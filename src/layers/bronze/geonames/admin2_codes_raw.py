# Full-refresh batch pull of GeoNames' admin2 (county-level) codes -- same
# reasoning as country_info_raw.py (single static file, no pagination/
# cursor; confirmed via a real fetch: 47,643 rows).
import sys

from pyspark import pipelines as dp
from pyspark.sql.functions import current_timestamp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.geonames import fetch_geonames_dump  # noqa: E402

ADMIN2_URL = spark.conf.get("geonames_admin2_codes_url")

# admin2Codes.txt has no header row at all (confirmed via a real fetch) --
# fieldnames supplied explicitly. Same shape as admin1CodesASCII.txt.
FIELDNAMES = ["code", "name", "asciiname", "geonameid"]

ATTRIBUTION = "This site or product includes GeoNames geographical data, https://www.geonames.org, licensed under CC BY 4.0."


@dp.materialized_view(comment=ATTRIBUTION)
def admin2_codes_raw():
    records = fetch_geonames_dump(ADMIN2_URL, FIELDNAMES)
    return spark.createDataFrame(records).withColumn("ingested_timestamp", current_timestamp())
