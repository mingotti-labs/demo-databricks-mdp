# Full-refresh batch pull of AirROI's /markets/metrics/all -- the
# time-series counterpart to market_summary_raw's single current
# snapshot. Real response shape (confirmed via a live test call against
# Urubici, one $0.10 call): {"market": {...}, "results": [...]}, where
# `results` is a rolling ~12-month window (one trailing month + ~11
# forward-looking/pacing months) of {date, occupancy, average_daily_rate,
# revpar, revenue, booking_lead_time, length_of_stay, min_nights,
# active_listings_count} -- each metric except active_listings_count is
# itself a distribution object ({avg, p25, p50, p75, p90}), not a single
# value like market_summary's flat fields.
#
# Landed source-faithful (one row per market per date, metric fields kept
# as-is) -- flattening the distribution structs into columns is a silver
# concern, not bronze.
#
# Same four markets as market_summary_raw -- see that file's header for
# why each was chosen/dropped. Every run re-calls the API for all four
# markets (this is a Materialized View, always fully recomputed) --
# 4 x $0.10 = $0.40 per run, same cost profile as market_summary_raw.
import sys

from pyspark import pipelines as dp
from pyspark.sql.functions import current_timestamp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.airroi import fetch_market_metrics_all  # noqa: E402

BASE_URL = spark.conf.get("airroi_base_url")
API_KEY = dbutils.secrets.get("airroi", "api_key")

MARKETS = [
    ("Brazil", "Bahia", "Vitória da Conquista", None),
    ("Brazil", "Santa Catarina", "Urubici", None),
    ("New Zealand", "Bay of Plenty", "Tauranga", None),
    ("Brazil", "Bahia", "Prado", "Cumuruxatiba"),
]


@dp.materialized_view()
def market_metrics_all_raw():
    records = []
    for country, region, locality, district in MARKETS:
        result = fetch_market_metrics_all(BASE_URL, API_KEY, country, region, locality, district)
        for entry in result["results"]:
            entry["_country"] = country
            entry["_region"] = region
            entry["_locality"] = locality
            entry["_district"] = district
            records.append(entry)
    return spark.createDataFrame(records).withColumn("ingested_timestamp", current_timestamp())
