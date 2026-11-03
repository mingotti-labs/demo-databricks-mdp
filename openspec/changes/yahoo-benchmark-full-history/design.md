## Context

See proposal.md. Probe P6 (`references/poc/macro-prices/p6_full_history_download.py`,
2026-11-03): `yf.download` with `start=1970-01-01`, one symbol, the fetch's own options,
returns each symbol's whole history:

| Symbol | Rows | From | Dividends |
|---|---|---|---|
| `^TRCCRB` | 8,174 | 1994-01-03 | 0 |
| `^SPGSCI` | 10,792 | 1984-01-03 | 0 |
| `GC=F`, `SI=F`, `HG=F` | about 6,570 each | 2000-08-30 | 0 |
| `CL=F` | 6,577 | 2000-08-23 | 0 |
| `DBC` | 5,218 | 2006-02-06 | 9 |
| `GSG` | 5,103 | 2006-07-21 | 0 |

State checked in prd (2026-11-03): `bronze_yahoo.fetch_state` has 517 rows, none for the
8 symbols; it is owned by the CI/CD service principal and the user has SELECT only on
`bronze_yahoo`. A direct insert is also blocked by the auto-mode classifier.

`plan()` today: no stored prices gives `(today - 365 days, reload=True)`; a symbol named
in `reload_symbols` reloads from its `first_price_date`.

## Goals / Non-Goals

**Goals:**
- Full history for the 8 commodity benchmarks in prd, loaded by the CI run itself, with
  no hand-written state.
- After that, the incremental rules are the same as for any symbol.

**Non-Goals:**
- Full history for S&P 500 symbols; extending the 14 older benchmarks; dev.

## Decisions

**D1. A new benchmark symbol loads all its history.** `plan(state, reload_symbols,
symbol, today, benchmarks)`: no stored prices and `symbol in benchmarks` returns
`(FULL_HISTORY_START, True)` with `FULL_HISTORY_START = 1970-01-01`. Yahoo returns
data from the symbol's first day, so the date only has to be early. 1970-01-01 is the
epoch: no negative timestamp reaches the API (probe P6 ran with it).

**D2. Rejected: `reload_symbols` for a new symbol.** It would make the parameter mean
"in full" for a new symbol too, but CI's own `run_yahoo` runs first with defaults and
loads the 8 as new symbols for one year. Making it work needs the job's default
`reload_symbols` set for one deploy and reset by a second PR (and a second CI run).

**D3. Rejected: a `history_start_date` column in `benchmarks.csv`.** Declarative and
permanent, but it adds a column through bronze raw, SCD2 (every row gets a new
version), Landing (a new column on a streaming table) and the checks, for eight rows;
the rule in D1 needs none of that.

**D4. Rejected: hand-seeding `fetch_state`.** Blocked by ownership and by the guardrail
on writes to `mdp_prd`.

**D5. Fix the pinned benchmarks count in the same change.** `reference_rows` 14 to 22
(the count after #143); it is a verification setting, so it is checked with the dev run
of `verify_bronze` for portfolio.

## Risks / Trade-offs

- [A benchmark added later also loads its full history] -> intended: benchmarks are
  few and are the long-run references; the cost is one download.
- [Older benchmarks keep one year, the new 8 get full history] -> accepted; extending
  the old ones needs their `fetch_state` rows reset, a separate decision.
- [Yahoo restates earlier adjusted closes on a later dividend, reloading the symbol in
  full] -> as today for any symbol; for `DBC` that now means its full history, about
  5,200 rows per distribution.
