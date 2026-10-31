## Context

See proposal.md. Probe P1 (`references/poc/fred-rates/`, result in
`p1_result.txt`) called the API from serverless with the key from the `fred`
scope, 2026-10-31:

- `series/observations?series_id=DGS10` returns 16,913 rows in one call (limit
  100,000), from 1962-01-02 to 2026-10-29, as
  `{"realtime_start", "realtime_end", "date", "value"}`. `value` is text; 721
  rows have the value `.` (market holidays), 16,192 have a number.
- `realtime_start` and `realtime_end` echo the request day; they change every
  day for every row, so they are not data.
- `series?series_id=DGS10` returns the title ("Market Yield on U.S. Treasury
  Securities at 10-Year Constant Maturity, Quoted on an Investment Basis"),
  `units` (Percent) and `frequency` (Daily).
- An unknown series returns HTTP 400 with an `error_message` in JSON.

Probe P1b (`p1b_result.txt`, same day) separates the two rates people call "the
US rate". On 2026-10-30:

| Series | What it is | Latest |
|---|---|---|
| `DGS10` | market yield on 10-year Treasuries; set by trading | 4.98 (2026-10-29) |
| `DFF` | effective federal funds rate (banks' overnight lending) | 3.88 (2026-10-29) |
| `DFEDTARU` / `DFEDTARL` | the Fed's target range, upper / lower | 4 / 3.75 (2026-10-30) |
| `FEDFUNDS` | monthly average of `DFF` | 3.75 (2026-09) |

The RBA cash rate target (`FIRMMCRTD`, 4.60) is the counterpart of the Fed's
target range, not of `DGS10`. `DFF` is daily and includes weekends (7-day);
`DFEDTARU/L` start 2008-12-16, when the Fed moved from a single target to a
range.

## Goals / Non-Goals

**Goals:**
- Daily `DGS10` and the Fed's policy rate (`DFF`, `DFEDTARU`, `DFEDTARL`), with
  room to add series by naming them.
- Raw files that replay without calling FRED, as RBA, SEC and Yahoo.

**Non-Goals:**
- Other series now; conversions; typed values.

## Decisions

**D1. Same shape as `rba-rates`.** One long table `observations`
(`series_id`, `observation_date`, `value`, `title`, `units`, `frequency`,
`ingested_timestamp`), so a second series costs no table. `observation_date`
stays `yyyy-MM-dd` text in raw and Publish and is a DATE in Landing, as RBA's.

**D2. Drop `.` values and the real-time columns in the fetch.** A day with no
value is no observation, as RBA's empty cells. `realtime_start/end` are left
out so the same value on two fetches differs only in `ingested_timestamp`.

**D3. Incremental by `observation_start`.** Per series, the last stored date
comes from `observations_raw`; the request asks from 31 days before it.
`reload=true`, or no stored rows, requests everything. FRED revises some
series for months, but not market yields; `reload=true` covers a revision.

**D4. The key never reaches a log.** `requests` puts the URL, query string
included, into exceptions, and the key is in the query string. The fetch checks
the status itself and raises `RuntimeError(f"FRED {path} {series_id}: HTTP
{status}: {error_message}")`, without the URL. The probe prints no URL either.
The key is read with `dbutils.secrets.get` in the notebook (the CI/CD
principal has READ on the scope); Databricks redacts a secret's value in
notebook output as well.

**D5. Series list in code**, `SERIES = ["DGS10", "DFF", "DFEDTARU", "DFEDTARL"]`
in `fred_series.py`; the base address is the bundle variable `fred_api_url`.
`FEDFUNDS` is left out: it is the monthly average of `DFF`.

**D6. Landing converts `observation_date`** with `to_date(col)` (the format is
the default `yyyy-MM-dd`), which fails the update under ANSI on a bad value, and
re-applies the "Natural key" comment, as RBA's Landing.

**D7. CI runs `run_fred` after a deploy** (free API, two calls per series).

**D8. Landing checks per source** (user, 2026-10-31). Each source gets
`verification/silver_landing_checks/<source>.yml`: `source`, `ingested_timestamp`
(true for the sources whose Bronze Publish carries it: airroi, iso, geonames,
acnc, wikipedia, portfolio, sec, yahoo, rba, fred) and `tables`, each with
`table`, `bronze_schema`, `bronze_table`, `scd2`. `src/common/silver_landing_checks.py`
loads and validates one file or all of them (the bronze checks' shape:
`load_spec`, required keys, tested without Spark); the notebook keeps its
checks and loses only the `ENTITIES` list and the
`SOURCES_WITH_INGESTED_TIMESTAMP` set. With `source` set and no file, the
notebook fails, as it does today for an unknown source. CI selects units from
files a resource names or imports, and a data file read by path at run time is
neither, so adding a file runs no other unit; this merge, which edits the
notebook, runs all of them once. Rejected: a separate change first. The prd
cost is the same (one all-units run), and it adds a full propose, implement
and archive cycle.

## Probes

**P1 (done, pass).** See Context. The result is in `p1_result.txt` and the
probes register.

## Dev results (2026-10-31)

Draft PR #127; everything ran as the service principal. The table quota read
430/500 before the runs.

- **Section 0, Landing checks per source.** Baseline, before any change: the
  `verify_silver_landing` job with an empty `source` verified 30 entities. After
  the refactor: 30 entities again; `source=yahoo` verified 4; `source=nope`
  failed with "no Silver Landing checks for source 'nope'". The 13 files load to
  exactly the old list (compared entry by entry: tables, SCD2 flags, timestamp
  flags). With `fred.yml` added the empty-`source` job verifies 31.
- **First `run_fred`** (`verify=true`): success. `observations_raw`,
  `observations_scd1` and `silver_landing.fred__observations` each hold 55,667
  rows: `DGS10` 16,192 (1962-01-02 to 2026-10-29, equal to P1's 16,913 less 721
  `.` days), `DFF` 26,419 (1954-07-01 to 2026-10-29), `DFEDTARU` and `DFEDTARL`
  6,528 each (2008-12-16 to 2026-10-30). In Landing: `DGS10` 4.98 (2026-10-29),
  `DFF` 3.88 (2026-10-29), `DFEDTARU` 4 and `DFEDTARL` 3.75 (2026-10-30),
  `observation_date` is DATE and `value` STRING.
- **Second run:** success, requested from 31 days before each series' last date
  and wrote 119 rows (`DFEDTARL` 32 from 2026-09-29, `DFEDTARU` 32 from
  2026-09-29, `DFF` 32 from 2026-09-28, `DGS10` 23 from 2026-09-28). Raw grew to
  55,786; Publish and Landing stayed at 55,667.
- `reload=true` was not run in dev: it requests the same observations as the
  first run.
- The API key is read from the `fred` scope; unit tests prove it is in no error
  message or traceback (`tests/common/test_fred_series.py`).

## Risks / Trade-offs

- [FRED changes the payload] -> The row builder indexes the keys it needs, so a
  missing one fails the fetch before anything is written.
- [Key rotated or revoked] -> The fetch fails with the HTTP status and FRED's
  message; no file is written (all series are requested before any file is).
- [The refactor drops or changes an entry] -> The dev Landing job with an empty
  `source` must report the same 30 entities before and after (31 with `fred`);
  a unit test fails when a source in `design_patterns.yml` has no check file.
- [This merge runs every unit in prd once] -> Accepted; it is the last time a
  new source does.

## Migration Plan

1. iac `raw-volume-fred` applied (volume `bronze_fred.s3_raw`).
2. Landing checks per source first: with the code unchanged, run the dev
   `verify_silver_landing` job with an empty `source` (30 entities); move the
   entries; run it again (30 entities, same result).
3. Draft PR deploys to dev; `run_fred` as the service principal with
   `verify=true`, then again to check the incremental request; the Landing job
   now reports 31 entities.
4. Merge; the notebook changed, so CI runs every unit in prd once.

Rollback: remove the code; drop the three tables per target with approval.
