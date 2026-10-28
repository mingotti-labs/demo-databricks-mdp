## Context

See proposal.md. What exists and shapes this change:

- Every snapshot source today has a Materialized View `_raw` recomputed on each
  run, feeding snapshot Auto CDC (bronze full pattern). On 2026-10-28 the user
  chose append-only, replayable raw for SEC and Yahoo (overwrite into a plain
  Delta table was rejected: raw would keep only the latest fetch).
- Clickstream is the repo's Auto Loader precedent (`web_events_raw`, streaming
  table over a volume, `addNewColumns`, schema location managed by the pipeline).
- `bronze_sec` has no volume yet (iac prerequisite in the proposal).
- Probe P5 (`references/docs/registers/probes.md`): concepts vary by company and
  over time; banks and insurers lack some figures; XOM's ticker now points to a
  holding company with no 10-K (predecessor CIK in `portfolio`).
- Lessons that constrain the shape: a snapshot flow cannot take a function
  source reading a dataset of its own pipeline (P6), and a Materialized View
  cannot be streamed (P8). A private view reading the raw table in batch is
  the source shape the existing sources already use.
- `verify_bronze` compares raw row count with SCD2 current rows and checks key
  uniqueness in raw; both are false for an append-only raw table.

## Goals / Non-Goals

**Goals:**
- Raw keeps every fetch, so silver can be rebuilt without calling SEC again.
- A weekly run with no new filings writes no SCD2 version and almost no raw rows.

**Non-Goals:**
- Choosing between concepts, picking the latest fiscal year, typing values
  (the `silver_investments` change).
- A schedule for `run_sec` (no run job has one yet; scheduling comes with the
  story's weekly refresh, in a later change).
- `frames` endpoint and filing documents.

## Decisions

- **D1 Fetch task writes files; Auto Loader appends.** A notebook task first in
  `run_sec` calls SEC and writes files to the volume; the pipeline only reads
  files. Rejected: fetching inside a streaming table (no streaming source for
  an HTTP API); a Materialized View (no history, the reason for this change);
  a job task writing Delta directly (raw would sit outside the pipeline, and the
  files are the replay copy anyway).
- **D2 Where the code lives.** Helpers in `src/common/sec_edgar.py` (fetch,
  flatten, hash, file names) with unit tests; the notebook in
  `src/common/fetch_sec.py`, next to `copy_repo_files.py`. Not in
  `src/layers/bronze/sec/`: the pipeline's `libraries` glob would run it as
  pipeline source.
- **D3 Files.** Paths follow NAMING.md "Volume paths":
  `/Volumes/<catalog>/bronze_sec/s3_raw/company_tickers/landing/<YYYY-MM-DD>/company_tickers_<fetch time>.jsonl`
  and `.../company_facts/landing/<YYYY-MM-DD>/<cik>_<fetch time>.jsonl`.
  JSON Lines, every value as text:
  - tickers: one row per entry of `company_tickers.json` (`cik` zero-padded to
    10, `ticker`, `title`). The SEC file is an object keyed by row number,
    which Auto Loader would read as one column per row; the reshape is the
    smallest that makes it a table.
  - facts: one row per reported value: `cik`, `entity_name`, `taxonomy`,
    `concept`, `unit`, `start`, `end`, `val`, `accn`, `fy`, `fp`, `form`,
    `filed`, `frame`, plus `ingested_timestamp` and `content_sha256` on every
    row. `ingested_timestamp` is the fetch time, one value per file, stamped by
    the task when it called SEC (NAMING.md: the fetch time of the data). Written
    in the file, it survives a replay; a pipeline-side `current_timestamp()`
    would tie when two files land before one pipeline run and would be
    rewritten by a full refresh. Only mapped concepts (D5).
  Rejected: landing the full `companyfacts` JSON. Its concept names are object
  keys (thousands of columns for Auto Loader) and it is 1 to 5 MB per company.
  SEC always returns the full history, so adding a concept to the mapping only
  needs a refetch, which happens on its own (D4).
- **D4 Write only what changed.** For each company the task hashes the sorted
  long-form rows and compares with that company's latest `content_sha256` in
  `bronze_sec.company_facts_raw`; it writes a file only when the hash differs
  or the company is new. On the first run (no table yet) every company is
  written. A mapping change alters every hash, so every company is rewritten
  once. Companies file a few times a year, so a weekly run writes a small
  share of files. Rejected: writing every company every week (about 52 times
  the raw rows for no new information).
- **D5 Inputs read by the task.** Current rows (`__END_AT IS NULL`) of
  `bronze_wikipedia_publish.sp500_constituents_scd2` (`cik`),
  `bronze_portfolio_publish.predecessor_ciks_scd2` (`predecessor_cik`) and
  `bronze_portfolio_publish.concept_mapping_scd2` (`taxonomy`, `concept`).
  Ordered by the job (`run_wikipedia` and `run_portfolio` run before it), not a
  pipeline dependency. Rejected: reading Silver Landing (bronze reads bronze;
  the story design names `bronze_portfolio`).
- **D6 Access.** `requests.Session` with the `User-Agent` from
  `http_user_agent` (task parameter), at most 10 requests per second (a minimum
  gap of 0.1 s between requests), one thread. HTTP 404 is logged and skipped
  (a CIK with no XBRL facts, such as a new holding company); any other non-200
  fails the task. URLs are constants in the helper (fixed public endpoints).
- **D7 Raw tables.** `@dp.table` streaming tables over Auto Loader
  (`cloudFiles.format=json`), with an explicit all-text schema (no inference)
  and `rescuedDataColumn`, plus the file path from `_metadata`
  (`ingested_timestamp` is stamped by our fetch task and read from the file, D3; SEC supplies no such time). Warn expectations: CIK is 10 digits; `concept`, `unit`, `end`,
  `val`, `accn` not null (facts); `ticker` not null (tickers). Warn, not drop:
  bronze keeps what SEC sent; silver decides. `company_facts_raw` and
  `company_facts_scd2` use automatic liquid clustering (`CLUSTER BY AUTO`);
  the tickers tables are small and do not.
- **D8 Snapshot of the latest file.** Private views feed snapshot Auto CDC:
  tickers from the rows with the latest `ingested_timestamp`; facts from each
  company's latest file (latest `ingested_timestamp` per `cik`). Platform
  columns (`ingested_timestamp`, `content_sha256`, file
  path, rescued data) are dropped from the snapshot. A company that leaves the
  index keeps its last facts as current (silver joins to membership). Keys:
  tickers `cik`, `ticker`; facts `cik`, `taxonomy`, `concept`, `unit`, `accn`,
  `start`, `end` (P1: unique over 47,133 rows of 20 companies; `fp`, `form` and
  `frame` add nothing). `start` is empty for point-in-time values (balance
  sheet, shares). The docs say nothing on missing key values in snapshot Auto
  CDC, so task 4.2 (an unchanged second run writes no version) is the check;
  if it fails, the snapshot view fills an empty `start` with `''` and the dev
  SCD2 table is dropped and rebuilt with the user's approval.
- **D9 Silver Landing** via `land_changes`, one file per table in
  `src/layers/silver/landing/sec/`, own silver pipeline, as Wikipedia.
- **D10 Verification of an append-only raw.** A new option in the bronze check
  spec, `compare_latest_file_per: [cik]` (an empty list means the latest fetch
  overall), the latest file found by `max(ingested_timestamp)` per group:
  the raw-side count and the key-uniqueness check use only the latest file
  per group instead of the whole table. Added to `src/common/bronze_checks.py`
  with unit tests. Silver Landing checks as usual.
- **D11 New pattern** `bronze_volume_append_autoloader_python` in the register
  (fetch task writes dated files, Auto Loader appends, snapshot SCD2 from the
  latest file per group), tagged on the two raw tables.
- **D12 Pipelines and job** as Wikipedia: `bronze--sec--<target>` and
  `silver--sec--<target>`, job `run_sec` with `fetch` first, then `bronze`,
  `verify_enabled`, `verify_bronze`, `silver`, `verify_silver`,
  `tag_patterns`.

## Probes

- **P1 Shape of the long-form facts** (before task 3): fetch 20 companies
  across sectors (including a bank, an insurer, a REIT, XOM's old CIK), flatten
  with the mapped concepts, report rows per company, nulls per key column and
  duplicate keys; extrapolate to 505 companies. Decides the D8 key and confirms
  the size fits Free Edition.
  **Result (2026-10-28, `references/poc/dividend-portfolio/p7_sec_long_form.py`):**
  22 CIKs, 49,599 rows; about 2,250 rows and 600 KB of JSON Lines per company,
  so about 1.14 million rows and 313 MB for 505 companies (raw SEC JSON is 3 to
  8 MB per company). No duplicate key with or without `frame`, and none on
  `cik`, `taxonomy`, `concept`, `unit`, `accn`, `start`, `end` (checked locally
  on 20 companies). Missing: `start` 15,714 rows (point-in-time values),
  `fp` 452, `frame` 32,870; no other key column. XOM's new CIK `0002115436`
  answers with 41 rows (not a 404); the old CIK `0000034088` has 2,425.
- **P2 `CLUSTER BY AUTO` from Python**: does `@dp.table` and
  `dp.create_streaming_table` accept automatic clustering on serverless Free
  Edition (`cluster_by_auto`)? If not, use explicit `cluster_by` on `cik`,
  `concept`.
  **Docs (2026-10-28):** both take `cluster_by_auto` (Python reference for
  `@dp.table` and `create_streaming_table`). Confirmed on the real tables in
  task 4.1 (`DESCRIBE DETAIL` shows clustering columns).

## Risks / Trade-offs

- [Raw grows with every changed file] → only changed companies are written
  (D4); clustering keeps reads by company cheap.
- [A full refresh of raw re-reads every file ever written] → that is the
  replay; the SCD2 table refuses a full refresh, so history stays.
- [SEC changes a value without a new filing] → the hash changes, a file is
  written, and SCD2 records the change: what raw history is for.
- [`company_facts_raw` is read by the fetch task while the pipeline owns it] →
  read only; on the first run the table does not exist and the task writes
  every company.
- [Long-form rows are a reshape, not the bytes SEC sent] → values are kept as
  text exactly as sent; only the nesting changes. Recorded in the source page.
- [SEC rate or blocking] → one thread at 10 per second with a contact
  `User-Agent`, SEC's published rule.

## Migration Plan

iac change applied first (volume and grants). Deploy to dev, run `run_wikipedia`
and `run_portfolio` if their tables are stale, then `run_sec` with
`verify=true` (first load, every company written). Run `run_sec` again at once:
almost no new files and no new SCD2 version. Stop the SQL warehouse after query
sessions. prd: CI deploys on merge and runs the unit. Rollback: remove the
resources; the volume files stay.

## Results (2026-10-28, dev)

- **First verified run** (`run_sec` with `verify=true`, every task succeeded,
  6 tables tagged): the fetch task wrote 501 facts files (500 index CIKs plus
  `0000034088`), no 404. Raw, SCD2 current and Landing rows: tickers 10,430;
  facts 1,077,402 for 500 companies. XOM's old CIK holds 2,425 current facts.
  No rescued data. Task times: fetch 21.3 min (mostly writing about 300 MB into
  the volume), bronze 3.2, silver 2.4.
- **Found and fixed:** Vylor Inc. (`0002128626`, new to SEC) has only
  filing-fee facts (`ffd`), so it wrote an empty file with no hash, which would
  be rewritten every run. The task now writes no file for a company with no
  mapped concept and reports it.
- **Second run, nothing changed** (task 4.2): 0 facts files written, 500
  unchanged, 1 with no mapped concept; tickers raw appended its second fetch
  (20,860 rows), SCD2 still 10,430 and 1,077,402 versions with 0 closed;
  verification passed on the latest file. The empty `start` key causes no
  spurious versions. Fetch 1.8 min, whole run 7.5 min.
- **P2:** `clusterByAuto` is `true` on `company_facts_raw` and
  `company_facts_scd2`; no clustering columns yet (Databricks chooses them from
  the queries it sees).
