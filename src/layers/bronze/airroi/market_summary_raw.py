# Full-refresh batch pull of AirROI's market summary data for three
# confirmed real markets -- Vitória da Conquista/BA, Urubici/SC,
# Tauranga/NZ. Sydney was explicitly dropped: its plain `sydney` slug on
# AirROI's own site sits alongside 50+ separate Sydney-suburb pages,
# strongly indicating it's a generic/residual bucket, not a real Local
# Government Area or the Greater Sydney metro. Tauranga has one accepted
# minor gap -- Papamoa, a real Tauranga suburb, is a separate sibling page
# and likely excluded from this market's figures.
#
# Same three markets in every environment (dev/tst/prd) -- unlike every
# other source, there's no free-tier/smaller-sample concept here (AirROI
# has no sandbox, every call costs real money), so per-environment
# row-limiting doesn't apply.
import sys

from pyspark import pipelines as dp

# Same sys.path fix unspsc_public_raw.py established -- see its header in
# ungm/ for why glob-including src/common in `libraries` alone doesn't
# work. Safe to use here since fetch_market_summary is a plain function,
# not a custom Spark DataSource class.
sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.airroi import fetch_market_summary  # noqa: E402

BASE_URL = spark.conf.get("airroi_base_url")
API_KEY = dbutils.secrets.get("airroi", "api_key")

# (country, region, locality) -- display names, matching the API's
# nested `market` object shape (confirmed via a real 422 response, not
# the flat country_code/state/city shown in AirROI's own published
# example for this endpoint). The market pages themselves use
# lowercase-hyphenated slugs (e.g. "vitória-da-conquista"); the API's
# market object expects display-style names instead.
MARKETS = [
    ("Brazil", "Bahia", "Vitória da Conquista"),
    ("Brazil", "Santa Catarina", "Urubici"),
    ("New Zealand", "Bay of Plenty", "Tauranga"),
]


@dp.materialized_view()
def market_summary_raw():
    records = []
    for country, region, locality in MARKETS:
        result = fetch_market_summary(BASE_URL, API_KEY, country, region, locality)
        result["_country"] = country
        result["_region"] = region
        result["_locality"] = locality
        records.append(result)
    return spark.createDataFrame(records)
