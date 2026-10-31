# Full-refresh batch pull of the ISO 10383 market identifier code list -- a
# single static CSV with no pagination and no incremental cursor (probe P1:
# 2,889 rows, unique MIC), so a Materialized View that re-fetches the whole file
# each run is the correct dataset type. Every row is kept (operating markets and
# segments, active and expired); the Silver Domain picks the operating ones.
import sys

from pyspark import pipelines as dp
from pyspark.sql.functions import current_timestamp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.iso10383 import fetch_market_identifier_codes  # noqa: E402

MIC_URL = spark.conf.get("iso10383_mic_url")

# ISO 10383 terms of use (October 2016): free use, but not reproducing all or a
# substantial part of the list for third parties -- recorded as a table comment.
ATTRIBUTION = (
    "Source: ISO 10383 Market Identifier Codes, ISO 10383 Registration Authority "
    "(https://www.iso20022.org/market-identifier-codes). Used under the ISO 10383 "
    "terms of use: do not reproduce all or a substantial part of the list for third parties."
)


@dp.materialized_view(comment=ATTRIBUTION)
def market_identifier_codes_raw():
    records = fetch_market_identifier_codes(MIC_URL)
    return spark.createDataFrame(records).withColumn("ingested_timestamp", current_timestamp())
