# sec-company-facts-ingestion Specification

## Purpose
SEC EDGAR tickers and company facts for the dividend portfolio story, fetched
into append-only, replayable raw files and tables, with SCD2 history and
Silver Landing.

## Requirements

### Requirement: Companies and concepts to fetch
Each run SHALL fetch company facts for every CIK currently in the S&P 500 list
(`bronze_wikipedia_publish`) plus every predecessor CIK currently in
`bronze_portfolio_publish.predecessor_ciks_scd2`, and SHALL keep only the facts
whose taxonomy and concept are in the current `portfolio` concept mapping. It
SHALL also fetch the SEC ticker list once per run.

#### Scenario: A predecessor CIK is fetched
- **WHEN** the predecessor list maps `0002115436` to `0000034088`
- **THEN** facts for `0000034088` are fetched even though it is not in the
  S&P 500 list

#### Scenario: Only mapped concepts are kept
- **WHEN** a company's facts include concepts that are not in the mapping
- **THEN** none of those concepts appear in the raw files or tables

### Requirement: Polite access to SEC
Every request SHALL send the `User-Agent` from the `http_user_agent` bundle
variable and the run SHALL make at most 10 requests per second. A company with
no facts (HTTP 404) SHALL be logged and skipped; any other failed request SHALL
fail the run.

#### Scenario: Rate stays under the limit
- **WHEN** a run fetches about 505 companies
- **THEN** it takes at least 50 seconds of request time and no request is
  refused by SEC for rate

### Requirement: Append-only raw files
Each fetch SHALL be written as a new dated file under
`/Volumes/<catalog>/bronze_sec/s3_raw/<data-source>/landing/`, never
overwriting or deleting an earlier file. Company facts SHALL be written in long
form (one row per company, concept, unit and reported value, values as SEC
sent them), one file per company, and only when that company's facts differ
from its last written file. The ticker list SHALL be written on every run.

#### Scenario: Unchanged company writes no file
- **WHEN** a company's facts are the same as in its last file
- **THEN** no new file is written for it

#### Scenario: Earlier files are kept
- **WHEN** a company's facts change
- **THEN** its new file is added and its earlier files are still in the volume

### Requirement: Append-only raw tables
`bronze_sec.company_tickers_raw` and `bronze_sec.company_facts_raw` SHALL be
streaming tables that append every new file's rows, stamping
`ingested_timestamp` as the time our fetch task called SEC, written by the task
into the file (so a replay keeps
it) and the file path, and SHALL record warn
expectations on the CIK format and on required fields. `company_facts_raw`
SHALL use automatic liquid clustering.

#### Scenario: Raw keeps every fetch
- **WHEN** two runs each write a file for the same company
- **THEN** `company_facts_raw` holds the rows of both files

#### Scenario: Raw can be rebuilt from the files
- **WHEN** the raw tables are fully refreshed
- **THEN** they are rebuilt from the files in the volume without calling SEC

### Requirement: Bronze Publish SCD2
`bronze_sec_publish.company_tickers_scd2` SHALL be built from the latest ticker
file and `bronze_sec_publish.company_facts_scd2` from each company's latest
file, by snapshot Auto CDC on their natural keys, following the bronze full
pattern (platform columns left out of the snapshot,
`pipelines.reset.allowed` false, change data feed on).

#### Scenario: Unchanged run writes no version
- **WHEN** the job runs and no company's facts changed
- **THEN** `company_facts_scd2` gets no new or closed version

#### Scenario: A new filing adds versions
- **WHEN** a company files new facts
- **THEN** its new facts are inserted as current versions and its other facts
  are unchanged

### Requirement: Silver Landing
`silver_landing_sec.company_tickers` and `silver_landing_sec.company_facts`
SHALL be built from the SCD2 change feeds with `land_changes`, keyed by the
same natural keys.

#### Scenario: Landing matches Bronze Publish
- **WHEN** the silver pipeline has run
- **THEN** each Landing table's current rows equal its SCD2 table's current rows

### Requirement: Run job and verification
Job `run_sec` SHALL run the fetch, the bronze pipeline, then (with
`verify=true`) bronze verification, the silver pipeline, Silver Landing
verification, and the design pattern tags.

#### Scenario: Verified run passes
- **WHEN** `run_sec` is run with `verify=true` in dev
- **THEN** every task succeeds
