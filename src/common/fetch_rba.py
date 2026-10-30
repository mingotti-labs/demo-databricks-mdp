# Databricks notebook source
# First task of run_rba: download RBA tables F11.1, F1, F2 and F5, turn each into
# one row per series and date, and write dated JSON Lines files into
# bronze_rba.s3_raw for Auto Loader to append. Files are never overwritten. After
# the first run only the rows from 31 days before a table's last stored date are
# written (src/common/rba_tables.py); reload=true writes every row.
# ingested_timestamp is this task's fetch time, written into every row, so a replay
# keeps it. Every file is downloaded and parsed before any is written, so a bad
# file leaves nothing behind.
import os
import sys
from datetime import UTC, datetime

import requests

dbutils.widgets.text("catalog", "")
dbutils.widgets.text("user_agent", "")
dbutils.widgets.text("tables_url", "")
dbutils.widgets.text("reload", "false")
dbutils.widgets.text("workspace_file_path", "")
catalog = dbutils.widgets.get("catalog")
user_agent = dbutils.widgets.get("user_agent")
tables_url = dbutils.widgets.get("tables_url")
reload = dbutils.widgets.get("reload") == "true"
sys.path.insert(0, f"{dbutils.widgets.get('workspace_file_path')}/src")
from common.rba_tables import TABLES, first_day, parse_table, since, stamp, to_jsonl

VOLUME = f"/Volumes/{catalog}/bronze_rba/s3_raw"
RAW = f"{catalog}.bronze_rba.observations_raw"

# COMMAND ----------

last_stored = {}
if spark.catalog.tableExists(RAW):
    last_stored = {
        row.table_id: row.last_date
        for row in spark.sql(
            f"""SELECT table_id, max(to_date(observation_date, 'dd-MMM-yyyy')) AS last_date
            FROM {RAW} GROUP BY table_id"""
        ).collect()
    }
print("last stored date per table:", last_stored, "| reload:", reload)

# COMMAND ----------

fetched = datetime.now(UTC)
ingested = fetched.isoformat()
files = {}
for table_id, name in TABLES.items():
    response = requests.get(
        f"{tables_url}/{name}", headers={"User-Agent": user_agent}, timeout=60
    )
    response.raise_for_status()
    rows = since(
        parse_table(table_id, response.text),
        first_day(last_stored.get(table_id), reload),
    )
    files[table_id] = stamp(rows, ingested)

# COMMAND ----------

folder = f"{VOLUME}/observations/landing/{fetched:%Y-%m-%d}"
os.makedirs(folder, exist_ok=True)
for table_id, rows in files.items():
    if not rows:
        print(f"{table_id}: no rows to write")
        continue
    path = f"{folder}/observations_{table_id}_{fetched:%Y%m%dT%H%M%SZ}.jsonl"
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(to_jsonl(rows))
    print(f"{table_id}: wrote {len(rows)} rows to {path}")
