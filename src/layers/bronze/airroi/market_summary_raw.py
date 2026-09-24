# Full-refresh batch pull of AirROI's market summary data for four
# confirmed real markets -- Vitória da Conquista/BA, Urubici/SC,
# Tauranga/NZ, and Cumuruxatiba/BA (queried as a *district* of Prado, not
# its own locality). Sydney was explicitly dropped: its plain `sydney`
# slug on AirROI's own site sits alongside 50+ separate Sydney-suburb
# pages, strongly indicating it's a generic/residual bucket, not a real
# Local Government Area or the Greater Sydney metro. Tauranga has one
# accepted minor gap -- Papamoa, a real Tauranga suburb, is a separate
# sibling page and likely excluded from this market's figures.
#
# Cumuruxatiba has no standalone market page on AirROI's site -- it only
# appears as a named neighborhood within Prado's report. Queried as
# locality="Prado" + district="Cumuruxatiba" (the `market` object's
# fourth field, unused by the other three markets). Confirmed via real
# calls that district is genuinely honored, not silently ignored:
# locality="Prado" alone returns 1,102.7 active listings; with
# district="Cumuruxatiba" it returns 360.6 -- a real, different subset,
# not a duplicate of Prado's aggregate.
#
# Same markets in every environment (dev/tst/prd) -- unlike every other
# source, there's no free-tier/smaller-sample concept here (AirROI has no
# sandbox, every call costs real money), so per-environment row-limiting
# doesn't apply.
import sys

from pyspark import pipelines as dp
from pyspark.sql.functions import current_timestamp

# Same sys.path fix unspsc_public_raw.py established -- see its header in
# ungm/ for why glob-including src/common in `libraries` alone doesn't
# work. Safe to use here since fetch_market_summary is a plain function,
# not a custom Spark DataSource class.
sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.airroi import fetch_market_summary  # noqa: E402

BASE_URL = spark.conf.get("airroi_base_url")
API_KEY = dbutils.secrets.get("airroi", "api_key")

# (country, region, locality, district) -- display names, matching the
# API's nested `market` object shape (confirmed via a real 422 response,
# not the flat country_code/state/city shown in AirROI's own published
# example for this endpoint). The market pages themselves use
# lowercase-hyphenated slugs (e.g. "vitória-da-conquista"); the API's
# market object expects display-style names instead.
MARKETS = [
    ("Brazil", "Bahia", "Vitória da Conquista", None),
    ("Brazil", "Santa Catarina", "Urubici", None),
    ("New Zealand", "Bay of Plenty", "Tauranga", None),
    ("Brazil", "Bahia", "Prado", "Cumuruxatiba"),
]


@dp.materialized_view()
def market_summary_raw():
    records = []
    for country, region, locality, district in MARKETS:
        result = fetch_market_summary(BASE_URL, API_KEY, country, region, locality, district)
        result["_country"] = country
        result["_region"] = region
        result["_locality"] = locality
        result["_district"] = district
        records.append(result)
    return spark.createDataFrame(records).withColumn("ingested_timestamp", current_timestamp())
