# Databricks notebook source
# First task of run_fred: fetch the FRED series in src/common/fred_series.py (the
# 10-year Treasury yield and the Fed's policy rate), drop the days with no value,
# and write one dated JSON Lines file into bronze_fred.s3_raw for Auto Loader to
# append. Files are never overwritten. After the first run only observations from
# 31 days before a series' last stored date are requested; reload=true requests
# everything. ingested_timestamp is this task's fetch time, written into every row,
# so a replay keeps it. Every series is fetched before any file is written, so a
# failed request leaves nothing behind. The API key goes in the query string, so
# requests are made only through get_json, which keeps it out of every error.
import os
import sys
from datetime import UTC, datetime

dbutils.widgets.text("catalog", "")
dbutils.widgets.text("api_url", "")
dbutils.widgets.text("reload", "false")
dbutils.widgets.text("workspace_file_path", "")
catalog = dbutils.widgets.get("catalog")
api_url = dbutils.widgets.get("api_url")
reload = dbutils.widgets.get("reload") == "true"
sys.path.insert(0, f"{dbutils.widgets.get('workspace_file_path')}/src")
from common.fred_series import (
    SERIES,
    first_day,
    get_json,
    observation_rows,
    series_info,
    stamp,
    to_jsonl,
)

VOLUME = f"/Volumes/{catalog}/bronze_fred/s3_raw"
RAW = f"{catalog}.bronze_fred.observations_raw"
key = dbutils.secrets.get("fred", "api_key")

# COMMAND ----------

last_stored = {}
if spark.catalog.tableExists(RAW):
    last_stored = {
        row.series_id: row.last_date
        for row in spark.sql(
            f"""SELECT series_id, max(to_date(observation_date)) AS last_date
            FROM {RAW} GROUP BY series_id"""
        ).collect()
    }
print("last stored date per series:", last_stored, "| reload:", reload)

# COMMAND ----------

fetched = datetime.now(UTC)
rows = []
for series_id in SERIES:
    info = series_info(get_json(api_url, key, "series", series_id))
    params = {}
    start = first_day(last_stored.get(series_id), reload)
    if start:
        params["observation_start"] = start.isoformat()
    payload = get_json(api_url, key, "series/observations", series_id, **params)
    series_rows = observation_rows(series_id, info, payload)
    print(f"{series_id}: {len(series_rows)} observations from {start or 'the start'}")
    rows += stamp(series_rows, fetched.isoformat())

# COMMAND ----------

if not rows:
    print("no rows to write")
else:
    folder = f"{VOLUME}/observations/landing/{fetched:%Y-%m-%d}"
    os.makedirs(folder, exist_ok=True)
    path = f"{folder}/observations_{fetched:%Y%m%dT%H%M%SZ}.jsonl"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(to_jsonl(rows))
    print(f"wrote {len(rows)} rows to {path}")
