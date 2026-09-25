# Full-refresh batch pull of ISO 3166-1 country codes -- the source is a
# single static CSV with no pagination and no incremental cursor (confirmed
# via a real fetch before this was written: 249 rows), so a Materialized
# View that re-fetches the whole file each run is the correct dataset type.
import sys

from pyspark import pipelines as dp
from pyspark.sql.functions import current_timestamp

# src/common isn't on the path by default -- glob-including it in this
# pipeline's `libraries` doesn't add it to sys.path (same ModuleNotFoundError
# UNGM's onboarding hit first). ${workspace.file_path} is threaded through
# via this pipeline's `configuration` block.
sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.iso3166 import fetch_iso3166_csv  # noqa: E402

COUNTRIES_URL = spark.conf.get("iso3166_countries_url")

# Required by the source data's CC BY-SA 4.0 license (ipregistry/iso3166 on
# GitHub) -- recorded as a Unity Catalog table comment, not just in repo
# docs, since this is externally-licensed data, not project-generated.
ATTRIBUTION = "This site or product includes Ipregistry ISO 3166 data available from https://ipregistry.co."


@dp.materialized_view(comment=ATTRIBUTION)
def country_codes_raw():
    records = fetch_iso3166_csv(COUNTRIES_URL)
    return spark.createDataFrame(records).withColumn("ingested_timestamp", current_timestamp())
