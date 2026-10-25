# Full-refresh pull of the S&P 500 constituents table from Wikipedia: one page,
# no pagination, no incremental cursor, so a Materialized View that re-fetches
# the whole table each run is the correct dataset type. Values stay as the page
# shows them (text, symbols with dots); the silver domain converts them.
import sys

from pyspark import pipelines as dp
from pyspark.sql.functions import current_timestamp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.wikipedia_sp500 import fetch_constituents  # noqa: E402

SP500_URL = spark.conf.get("wikipedia_sp500_url")
USER_AGENT = spark.conf.get("http_user_agent")

# Wikipedia text is CC BY-SA 4.0, so the attribution is a table comment.
ATTRIBUTION = (
    "Source: Wikipedia, List of S&P 500 companies "
    "(https://en.wikipedia.org/wiki/List_of_S%26P_500_companies), licensed CC BY-SA 4.0."
)


@dp.materialized_view(comment=ATTRIBUTION)
def sp500_constituents_raw():
    records = fetch_constituents(SP500_URL, USER_AGENT)
    return spark.createDataFrame(records).withColumn("ingested_timestamp", current_timestamp())
