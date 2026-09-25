# Full-refresh batch pull of ISO 3166-2 subdivision codes -- same reasoning
# as country_codes_raw.py (single static CSV, no pagination/cursor;
# confirmed via a real fetch: 6,260 rows).
import sys

from pyspark import pipelines as dp
from pyspark.sql.functions import current_timestamp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.iso3166 import fetch_iso3166_csv  # noqa: E402

SUBDIVISIONS_URL = spark.conf.get("iso3166_subdivisions_url")

ATTRIBUTION = "This site or product includes Ipregistry ISO 3166 data available from https://ipregistry.co."


@dp.materialized_view(comment=ATTRIBUTION)
def subdivision_codes_raw():
    records = fetch_iso3166_csv(SUBDIVISIONS_URL)
    # The source column name contains a hyphen, which isn't a valid Spark
    # DataFrame column identifier on its own -- renamed on ingest. The
    # schema name already implies "ISO 3166-2," so the shorter
    # `subdivision_code` is used rather than `subdivision_code_iso3166_2`.
    df = spark.createDataFrame(records)
    return df.withColumnRenamed("subdivision_code_iso3166-2", "subdivision_code").withColumn(
        "ingested_timestamp", current_timestamp()
    )
