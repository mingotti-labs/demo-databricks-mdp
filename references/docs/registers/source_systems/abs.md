# ABS (Australian Bureau of Statistics)

Consumer Price Index through the ABS Data API (SDMX REST, `data.api.abs.gov.au/rest`).
No key, no stated rate limit; a run makes two requests.

- URL: bundle variable `abs_api_url`, same for every target.
- Code: `src/common/abs_series.py` (request, rows), `src/common/fetch_abs.py` (first
  task of `run_abs`), `src/layers/bronze/abs/`, `src/layers/bronze/abs_publish/`,
  `src/layers/silver/landing/abs/`.
- Dataflow `ABS,CPI,2.0.0`. Structure URLs use the slash form (`/dataflow/ABS/CPI/2.0.0`),
  data URLs the comma form (`/data/ABS,CPI,2.0.0/<key>`). The key is
  `MEASURE.INDEX.TSEST.REGION.FREQ`.

## Series fetched

| Key | What it is | From | Rows (2026-11-03) |
|---|---|---|---|
| `1.10001.10.50.Q` | all groups CPI, Australia, original, quarterly | 1948-Q3 | 313 |
| `1.10001.10.50.M` | same, monthly | 2024-04 | 30 |

Index numbers on the latest reference base (`Sep 2025 = 100.0`). The monthly series
only exists from 2024-04. A seasonally adjusted monthly series (`TSEST` 20) answers
404. Add a series by naming its key in `SERIES` in `abs_series.py`.

## Shape and gotchas

- `format=csvfilewithlabels` gives a code column and a label column per dimension.
  Rows come back unsorted; `value` is text and `time_period` is a quarter or month
  (`1948-Q3`, `2024-04`), kept as text in every layer.
- Every run fetches the whole history (the ABS restates it when it rebases the index),
  so raw grows by 343 rows a run. Bronze Publish is SCD2 by `series_key`, `time_period`
  (bronze full pattern: the snapshot is the latest file without its fetch time, so a
  run with the same values writes nothing and a rebase closes the old versions).
- A non-200 status or an empty answer fails the task with the key and status.
- Probes: P4 (laptop) and P7 (serverless) in `references/docs/registers/probes.md`.
