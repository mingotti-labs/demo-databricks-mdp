# Databricks notebook source
# First task of run_abs: fetch the ABS CPI series in src/common/abs_series.py (all
# groups, Australia, quarterly and monthly) and write one dated JSON Lines file into
# bronze_abs.s3_raw for Auto Loader to append. Files are never overwritten. Every run
# fetches the whole history, because the ABS restates it when it rebases the index.
# ingested_timestamp is this task's fetch time, written into every row, so a replay
# keeps it. Every series is fetched before any file is written, so a failed request
# leaves nothing behind.
import os
import sys
from datetime import UTC, datetime

dbutils.widgets.text("catalog", "")
dbutils.widgets.text("api_url", "")
dbutils.widgets.text("workspace_file_path", "")
catalog = dbutils.widgets.get("catalog")
api_url = dbutils.widgets.get("api_url")
sys.path.insert(0, f"{dbutils.widgets.get('workspace_file_path')}/src")
from common.abs_series import SERIES, get_csv, observation_rows, stamp, to_jsonl

VOLUME = f"/Volumes/{catalog}/bronze_abs/s3_raw"

# COMMAND ----------

fetched = datetime.now(UTC)
rows = []
for series_key in SERIES:
    series_rows = observation_rows(series_key, get_csv(api_url, series_key))
    first, last = series_rows[0]["time_period"], series_rows[-1]["time_period"]
    print(f"{series_key}: {len(series_rows)} observations, {first} to {last}")
    rows += stamp(series_rows, fetched.isoformat())

# COMMAND ----------

folder = f"{VOLUME}/observations/landing/{fetched:%Y-%m-%d}"
os.makedirs(folder, exist_ok=True)
path = f"{folder}/observations_{fetched:%Y%m%dT%H%M%SZ}.jsonl"
with open(path, "w", encoding="utf-8") as handle:
    handle.write(to_jsonl(rows))
print(f"wrote {len(rows)} rows to {path}")
