## Context

See proposal.md. Probe P2 (`references/poc/macro-prices/p2_fred_cpi.py`, result in
`p2_result.txt`, 2026-11-02) read the three series from FRED's public graph CSV,
which serves the same observations as the API:

| Series | What it is | From | Last (2026-09-01) |
|---|---|---|---|
| `CPIAUCSL` | CPI-U all items, seasonally adjusted | 1947-01-01 | 336.298 |
| `CPIAUCNS` | CPI-U all items, not seasonally adjusted | 1913-01-01 | 336.940 |
| `CPILFESL` | CPI-U less food and energy, seasonally adjusted | 1957-01-01 | 338.896 |

All three are monthly and dated the first day of the month they measure. The index
base is 1982-84 = 100. September's value was published in mid-October, so a value's
date is not the day it became known; the silver domain change decides how to use
that (agreed: carry forward from the period start).

`src/common/fetch_fred.py` reads the last stored `observation_date` per series from
`observations_raw`; a series with none is requested in full. So the first run after
the merge loads each CPI series' whole history and the existing series stay
incremental.

## Goals / Non-Goals

**Goals:**
- Monthly US CPI (headline, both adjustments, and core) in Silver Landing, with
  no new tables.

**Non-Goals:**
- CPI in `market_rate_daily`, daily rows, inflation rates (later changes).
- Other countries' CPI (ABS is change 3; New Zealand and Brazil are parked).
- Release dates (FRED's real-time and vintage data, ALFRED).

## Decisions

**D1. Add the series to the existing source, not a new one.** FRED already holds
the key, the volume, the long table and the run job; a long table takes any series.
Rejected: BLS's own API (a second key and source for the same numbers).

**D2. Three series.** `CPIAUCNS` is the one published inflation is computed from
and is never revised. `CPIAUCSL` is the smoothed month-to-month view. `CPILFESL`
(core) is the measure central banks watch for underlying inflation. Rejected:
regional and item-level CPI series (not needed by the story).

**D3. Keep the 31-day lookback; reload once a year.** Each February the BLS revises
the seasonally adjusted series (`CPIAUCSL`, `CPILFESL`) for the previous five years.
The 31-day lookback would keep the old values for those years. Rather than a lookback
per frequency, a `run_fred` run with `reload=true` after the February release takes
the revisions (about 60,000 rows, as the first load). `CPIAUCNS` is never revised.
Documented in the FRED source system file. Rejected: a five-year lookback for monthly
series (code for a once-a-year event).

## Risks / Trade-offs

- [The yearly reload is a manual step and can be forgotten] -> the revisions are
  small; the not-adjusted series, used for inflation, is never revised.
- [A series renamed or retired by FRED] -> the fetch fails with FRED's 400 message,
  as for any unknown series.
