# SEC EDGAR

The SEC's ticker list and XBRL company facts. Free, no key, public domain.

- Endpoints: `https://www.sec.gov/files/company_tickers.json` (about 10,400
  tickers) and `https://data.sec.gov/api/xbrl/companyfacts/CIK<10 digits>.json`
  (one company, every concept and every filing, 3 to 8 MB).
- Access: SEC requires a contact `User-Agent` (bundle variable
  `http_user_agent`) and at most 10 requests per second; the client keeps a
  0.1 s gap, one thread.
- Code: `src/common/sec_edgar.py` (client, long-form rows, hash),
  `src/common/fetch_sec.py` (first task of `run_sec`),
  `src/layers/bronze/sec/`, `src/layers/bronze/sec_publish/`,
  `src/layers/silver/landing/sec/`.

## Files and raw tables

- The fetch task writes JSON Lines into `bronze_sec.s3_raw`:
  `company_tickers/landing/<date>/company_tickers_<fetch time>.jsonl` every run,
  and `company_facts/landing/<date>/<cik>_<fetch time>.jsonl` only when a
  company's facts changed since its last file (`content_sha256`). Files are
  never overwritten or deleted.
- Facts are reshaped to long form (one row per company, concept, unit and
  reported value) and kept only for the concepts in the `portfolio` concept
  mapping. Values stay text as SEC sent them; only the nesting changes. SEC
  always returns the full history, so a new mapped concept needs only the next
  run (every hash changes, every company is rewritten once).
- `ingested_timestamp` is written by our fetch task (the time it called SEC);
  SEC supplies no such time. `filed` and `end` are SEC's own dates.

## Shape and gotchas

- About 2,150 rows per company for the 35 mapped concepts: 1.08 million rows in
  the first load (dev, 2026-10-28).
- `start` is empty for point-in-time values (balance sheet, shares); `fp` and
  `frame` are often empty. The key `cik, taxonomy, concept, unit, accn, start,
  end` is unique (probe P7); the empty `start` causes no spurious SCD2 versions.
- XOM's ticker now maps to ExxonMobil Holdings Corp (`0002115436`, a few facts
  only); the history is under `0000034088`, fetched as a predecessor CIK.
- A new company may have only filing-fee facts (`ffd`), so no mapped concept:
  no file is written for it (Vylor Inc. `0002128626` in the first load).
- `company_tickers.json` is an object keyed by row number; the task writes one
  row per ticker with the CIK zero-padded.
- First load: the fetch task took 21 minutes, mostly writing about 300 MB into
  the volume; an unchanged run took under 2 minutes.
