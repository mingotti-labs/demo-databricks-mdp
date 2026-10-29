# Databricks notebook source
# MAGIC %pip install yfinance==1.7.0

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

# First task of run_yahoo: fetch Yahoo prices, events (dividends, splits),
# calendar and options for every symbol ever in the S&P 500 list plus the
# portfolio benchmarks, in batches, writing dated JSON Lines into
# bronze_yahoo.s3_raw for Auto Loader to append. Prices are incremental (from the
# last stored day minus one); a symbol is reloaded in full when it is new, has a
# dividend or split in the new days, or is named in reload_symbols.
# bronze_yahoo.fetch_state is updated after each batch's files are written, so a
# repair of the same run skips the symbols it already fetched. The only notebook
# allowed %pip (CLAUDE.md guardrails): a notebook task cannot declare a library.
import logging
import os
import sys
from datetime import UTC, date, datetime, timedelta

import yfinance as yf

dbutils.widgets.text("catalog", "")
dbutils.widgets.text("workspace_file_path", "")
dbutils.widgets.text("reload_symbols", "")
dbutils.widgets.text("run_id", "")
catalog = dbutils.widgets.get("catalog")
run_id = dbutils.widgets.get("run_id")
reload_symbols = {s.strip() for s in dbutils.widgets.get("reload_symbols").split(",") if s.strip()}
sys.path.insert(0, f"{dbutils.widgets.get('workspace_file_path')}/src")
from common.yahoo_market import (
    calendar_row,
    event_rows,
    has_new_event,
    monthly_expiry,
    option_row,
    plan,
    price_rows,
    stamp,
    to_jsonl,
    yahoo_symbol,
)

logging.getLogger("yfinance").setLevel(logging.CRITICAL)
VOLUME = f"/Volumes/{catalog}/bronze_yahoo/s3_raw"
STATE = f"{catalog}.bronze_yahoo.fetch_state"
BATCH_SIZE = 50
MAX_MISSING_SHARE = 0.02

# COMMAND ----------

spark.sql(
    f"""
    CREATE TABLE IF NOT EXISTS {STATE} (
      symbol STRING, yahoo_symbol STRING, first_price_date STRING, last_price_date STRING,
      last_run_id STRING, last_fetched_timestamp TIMESTAMP, last_outcome STRING
    ) COMMENT 'Yahoo fetch progress per symbol, written only by src/common/fetch_yahoo.py'
    """
)
members = {
    row.symbol
    for row in spark.sql(
        f"""SELECT symbol FROM {catalog}.bronze_wikipedia_publish.sp500_constituents_scd2
        WHERE __END_AT IS NULL"""
    ).collect()
}
symbols = sorted(
    row.symbol
    for row in spark.sql(
        f"""
        SELECT DISTINCT symbol FROM {catalog}.bronze_wikipedia_publish.sp500_constituents_scd2
        UNION
        SELECT symbol FROM {catalog}.bronze_portfolio_publish.benchmarks_scd2 WHERE __END_AT IS NULL
        """
    ).collect()
)
state = {row.symbol: row.asDict() for row in spark.table(STATE).collect()}
pending = [s for s in symbols if state.get(s, {}).get("last_run_id") != run_id]
print(f"{len(symbols)} symbols ({len(members)} current members), {len(pending)} to fetch")

# COMMAND ----------


def write(dataset: str, fetched: datetime, batch: int, rows: list[dict]) -> None:
    if not rows:
        return
    folder = f"{VOLUME}/{dataset}/landing/{fetched:%Y-%m-%d}"
    os.makedirs(folder, exist_ok=True)
    name = f"{dataset}_{fetched:%Y%m%dT%H%M%SZ}_{batch:03d}.jsonl"
    with open(f"{folder}/{name}", "w", encoding="utf-8") as handle:
        handle.write(to_jsonl(rows))


def download(group: list[str], start: date, today: date) -> dict:
    """Daily prices with dividends and splits, per symbol, in one bulk call."""
    data = yf.download(
        [yahoo_symbol(s) for s in group],
        start=start.isoformat(),
        end=(today + timedelta(days=1)).isoformat(),
        auto_adjust=False,
        actions=True,
        group_by="ticker",
        threads=True,
        progress=False,
    )
    return {s: data[yahoo_symbol(s)].dropna(subset=["Close"]) for s in group}


def fetch_prices(batch: list[str], today: date) -> tuple[dict, set[str]]:
    """Prices per symbol and the symbols reloaded in full."""
    plans = {s: plan(state.get(s), reload_symbols, s, today) for s in batch}
    frames, reloads = {}, {s for s, (_, reload) in plans.items() if reload}
    for start in sorted({start for s, (start, reload) in plans.items() if not reload}):
        group = [s for s, (begin, reload) in plans.items() if not reload and begin == start]
        for symbol, frame in download(group, start, today).items():
            if len(frame) and has_new_event(frame, state[symbol]["last_price_date"]):
                reloads.add(symbol)
            else:
                frames[symbol] = frame
    for symbol in reloads:
        start = plan(state.get(symbol), {"*"}, symbol, today)[0]
        frames.update(download([symbol], start, today))
    return frames, reloads


def fetch_details(symbol: str, reload: bool, today: date) -> tuple[list, list, list]:
    """Full events (on reload), calendar and options for one symbol."""
    ticker = yf.Ticker(yahoo_symbol(symbol))
    events = event_rows(symbol, ticker.actions) if reload else []
    calendar = [calendar_row(symbol, ticker.calendar)]
    expiries = ticker.options
    expiry = monthly_expiry(expiries, today)
    chain = ticker.option_chain(expiry) if expiry else None
    return events, calendar, [option_row(symbol, expiries, expiry, chain)]


def save_state(batch: list[str], frames: dict, reloads: set[str], fetched: datetime) -> None:
    """Merge the batch's progress; a symbol with no prices keeps its run id for a retry."""
    rows = []
    for symbol in batch:
        frame = frames.get(symbol)
        old = state.get(symbol) or {}
        if frame is None or not len(frame):
            rows.append(
                (
                    symbol,
                    yahoo_symbol(symbol),
                    old.get("first_price_date"),
                    old.get("last_price_date"),
                    old.get("last_run_id"),
                    fetched,
                    "no_prices",
                )
            )
            continue
        first = frame.index.min().date().isoformat()
        if symbol not in reloads and old.get("first_price_date"):
            first = min(first, old["first_price_date"])
        rows.append(
            (
                symbol,
                yahoo_symbol(symbol),
                first,
                frame.index.max().date().isoformat(),
                run_id,
                fetched,
                "reloaded" if symbol in reloads else "fetched",
            )
        )
    spark.createDataFrame(rows, spark.table(STATE).schema).createOrReplaceTempView("batch_state")
    spark.sql(
        f"""MERGE INTO {STATE} t USING batch_state s ON t.symbol = s.symbol
        WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT *"""
    )


# COMMAND ----------

today = datetime.now(UTC).date()
counts = {"prices": 0, "events": 0, "calendar": 0, "options": 0, "reloaded": 0, "detail_errors": 0}
for number, offset in enumerate(range(0, len(pending), BATCH_SIZE)):
    batch = pending[offset : offset + BATCH_SIZE]
    fetched = datetime.now(UTC)
    ingested = fetched.isoformat()
    frames, reloads = fetch_prices(batch, today)
    prices, events, calendars, options = [], [], [], []
    for symbol in batch:
        frame = frames.get(symbol)
        if frame is None or not len(frame):
            continue
        prices += price_rows(symbol, frame)
        if symbol not in reloads:
            events += event_rows(symbol, frame)
        try:
            more_events, calendar, option = fetch_details(symbol, symbol in reloads, today)
        except Exception as error:  # noqa: BLE001 - one symbol's details never fail the run
            print(f"details failed for {symbol}: {type(error).__name__}: {error}")
            counts["detail_errors"] += 1
            continue
        events += more_events
        calendars += calendar
        options += option
    for dataset, rows in [
        ("prices", prices),
        ("events", events),
        ("calendar", calendars),
        ("options", options),
    ]:
        write(dataset, fetched, number, stamp(rows, ingested))
        counts[dataset] += len(rows)
    counts["reloaded"] += len(reloads)
    save_state(batch, frames, reloads, fetched)
    print(f"batch {number}: {len(batch)} symbols, {len(prices)} prices, {len(reloads)} reloaded")

# COMMAND ----------

done = {row.symbol for row in spark.table(STATE).where(f"last_run_id = '{run_id}'").collect()}
missing_members = sorted(members - done)
missing_others = sorted(set(symbols) - members - done)
print(f"members with no prices: {missing_members}")
print(f"former members and benchmarks with no prices: {missing_others}")
summary = ", ".join(f"{k} {v}" for k, v in counts.items())
summary += f", members missing {len(missing_members)}, others missing {len(missing_others)}"
if len(missing_members) > MAX_MISSING_SHARE * len(members):
    raise RuntimeError(f"more than 2% of members have no prices: {summary}")
dbutils.notebook.exit(summary)
