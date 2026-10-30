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

## Probes

**P1 (done, pass).** See Context. The result is in `p1_result.txt` and the
probes register.

## Risks / Trade-offs

- [FRED changes the payload] -> The row builder indexes the keys it needs, so a
  missing one fails the fetch before anything is written.
- [Key rotated or revoked] -> The fetch fails with the HTTP status and FRED's
  message; no file is written (all series are requested before any file is).
- [Verification entry runs every unit in prd] -> Accepted, as for RBA; a later
  small change can move the Landing checks into per-source files.

## Migration Plan

1. iac `raw-volume-fred` applied (volume `bronze_fred.s3_raw`).
2. Draft PR deploys to dev; `run_fred` as the service principal with
   `verify=true`, then again to check the incremental request.
3. Merge; CI runs `run_fred` (and the other units) in prd.

Rollback: remove the code; drop the three tables per target with approval.
