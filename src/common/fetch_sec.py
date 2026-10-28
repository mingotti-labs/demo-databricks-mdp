# Databricks notebook source
# First task of run_sec: fetch SEC's ticker list and the company facts of every
# current S&P 500 CIK plus the predecessor CIKs, keep only the mapped concepts,
# and write dated JSON Lines files into bronze_sec.s3_raw for Auto Loader to
# append. Files are never overwritten. A company's facts file is written only
# when its content differs from its last file (content_sha256 in
# company_facts_raw); the ticker list is written every run. ingested_timestamp is
# this task's fetch time, written into every row, so a replay keeps it.
import os
import sys
from datetime import UTC, datetime

dbutils.widgets.text("catalog", "")
dbutils.widgets.text("user_agent", "")
dbutils.widgets.text("workspace_file_path", "")
catalog = dbutils.widgets.get("catalog")
user_agent = dbutils.widgets.get("user_agent")
sys.path.insert(0, f"{dbutils.widgets.get('workspace_file_path')}/src")
from common.sec_edgar import (
    SecClient,
    content_sha256,
    fact_rows,
    stamp,
    ticker_rows,
    to_jsonl,
)

VOLUME = f"/Volumes/{catalog}/bronze_sec/s3_raw"
FACTS_RAW = f"{catalog}.bronze_sec.company_facts_raw"

# COMMAND ----------

ciks = sorted(
    {
        row.cik
        for row in spark.sql(
            f"""
            SELECT cik FROM {catalog}.bronze_wikipedia_publish.sp500_constituents_scd2
            WHERE __END_AT IS NULL
            UNION
            SELECT predecessor_cik FROM {catalog}.bronze_portfolio_publish.predecessor_ciks_scd2
            WHERE __END_AT IS NULL
            """
        ).collect()
    }
)
concepts = {
    (row.taxonomy, row.concept)
    for row in spark.sql(
        f"""
        SELECT taxonomy, concept FROM {catalog}.bronze_portfolio_publish.concept_mapping_scd2
        WHERE __END_AT IS NULL
        """
    ).collect()
}
previous = {}
if spark.catalog.tableExists(FACTS_RAW):
    previous = {
        row.cik: row.sha
        for row in spark.sql(
            f"SELECT cik, max_by(content_sha256, ingested_timestamp) AS sha FROM {FACTS_RAW} GROUP BY cik"
        ).collect()
    }
print(f"{len(ciks)} companies, {len(concepts)} concepts, {len(previous)} with a previous file")

# COMMAND ----------


def write(data_source: str, name: str, fetched: datetime, rows: list[dict]) -> None:
    folder = f"{VOLUME}/{data_source}/landing/{fetched:%Y-%m-%d}"
    os.makedirs(folder, exist_ok=True)
    with open(f"{folder}/{name}_{fetched:%Y%m%dT%H%M%SZ}.jsonl", "w", encoding="utf-8") as handle:
        handle.write(to_jsonl(rows))


client = SecClient(user_agent)
fetched = datetime.now(UTC)
ingested = fetched.isoformat()
write("company_tickers", "company_tickers", fetched, stamp(ticker_rows(client.tickers()), ingested))

written, unchanged, missing = 0, 0, []
for cik in ciks:
    payload = client.facts(cik)
    if payload is None:
        missing.append(cik)
        continue
    rows = fact_rows(cik, payload, concepts)
    sha = content_sha256(rows)
    if previous.get(cik) == sha:
        unchanged += 1
        continue
    write("company_facts", cik, fetched, stamp(rows, ingested, sha))
    written += 1

print(f"no facts (404): {missing}")
dbutils.notebook.exit(
    f"facts files written {written}, unchanged {unchanged}, no facts {len(missing)}"
)
