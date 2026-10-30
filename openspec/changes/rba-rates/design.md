## Context

See proposal.md. The four RBA files share one layout, checked 2026-10-31:

```
F11.1  EXCHANGE RATES                      <- table title
Title,A$1=USD,Trade-weighted Index ...     <- one column per series
Description,...
Frequency,Daily,...
Type,Indicative,...
Units,USD,Index,...
(blank lines)
Source,WM/Reuters,RBA,...
Publication date,30-Oct-2026,...
Series ID,FXRUSD,FXRTWI,...
03-Jan-2023,0.6828,61.40,...               <- one row per date
```

| Table | Content | Series | Dates | From | Frequency | Values |
|---|---|---|---|---|---|---|
| F11.1 | exchange rates | 23 | 962 | 03-Jan-2023 | daily | 18,938 |
| F1 | money market, cash rate target | 17 | 4,007 | 04-Jan-2011 | daily | 46,902 |
| F2 | government bond yields | 5 | 3,406 | 20-May-2013 | daily | 16,298 |
| F5 | indicator lending rates, housing | 30 | 813 | 31-Jan-1959 | monthly | 7,824 |

Dates are `dd-Mon-yyyy` in all four. Recent F1 dates leave most cells empty
until the RBA fills them. The files start with a byte order mark. Exchange
rates before 2023 are only in Excel files (`f11hist.xls`,
`f11hist-1969-2009.xls`). Table F6 (rates on outstanding housing loans) writes
dates as `dd/mm/yyyy` and starts in 2019, so it is left out; `F2.1` and `F1.1`
are monthly copies of F2 and F1.

The metastore table quota read 458/500 on 2026-10-31 (it counts each
streaming table twice, for its hidden twin).

## Goals / Non-Goals

**Goals:**
- Daily AUD/USD and the cash rate target, with every other series of the two
  tables kept at no extra table cost.
- Raw files that replay without calling the RBA, as SEC and Yahoo.

**Non-Goals:**
- Exchange rates before 2023; other RBA tables; FRED.
- Typed values or conversions (silver domain).

## Decisions

**D1. One long table for all RBA tables.** Rows are
`(table_id, series_id, observation_date, value)` plus the series metadata.
Three tables per RBA table would take 48 slots instead of 12 for no
query gain: every consumer filters by `series_id`. Rejected: one wide table
per RBA table (series as columns), which breaks when the RBA adds a series.

**D2. The fetch writes long JSON Lines, not the CSV.** The header rows are
not data, so Auto Loader cannot read the CSV as it is. The fetch parses it in
`src/common/rba_tables.py` (pure functions, unit tested) and writes one file
per table per run to
`/Volumes/<catalog>/bronze_rba/s3_raw/observations/landing/<date>/observations_<table_id>_<UTC stamp>.jsonl`
(a dated folder, as Yahoo). All four files are downloaded and parsed before any
is written, so a bad file leaves nothing behind.
Values stay text as the RBA wrote them, including the date (`03-Jan-2023`).
`ingested_timestamp` is the fetch time, written into every row (one value per
file), as SEC and Yahoo.

**D3. Write only the last 31 days after the first run.** The fetch reads the
last stored date per table from `bronze_rba.observations_raw` and writes rows
dated from 31 days before it. That keeps late-filled F1 cells and short
revisions (and for F5, whose dates are month ends, the previous month), and
keeps raw growth to about 1,200 rows a run. An empty raw table
or `reload=true` writes every row. Rejected: writing the whole file each run
(about 120,000 rows a week, almost all repeats).

**D4. Publish is SCD1 by `(series_id, observation_date)`**, sequenced by
`ingested_timestamp`: the latest value wins, and a revision is an update.
History of revisions stays in raw. Same pattern as Yahoo's prices.

**D5. Silver Landing `silver_landing.rba__observations`** through
`land_changes`, keyed by `series_id` and `observation_date`. Landing turns
`observation_date` and `publication_date` into dates (user, 2026-10-31, before
merge); `value` and the rest stay text, as other sources' Landing tables keep
Bronze's types. The conversion is `to_date(col, 'dd-MMM-yyyy')`, which under
ANSI fails the update on a value that does not read as a date, and the
"Natural key" column comment is re-applied after it. Dev's first Landing table
had text dates, so it was rebuilt once with a full refresh of the silver
pipeline (Landing is derived from Publish's change feed).

**D6. Table list in code.** `rba_tables.py` holds
`TABLES = {"F11.1": "f11.1-data.csv", "F1": "f1-data.csv", "F2": "f2-data.csv",
"F5": "f5-data.csv"}`; the bundle
variable `rba_tables_url` holds the base address. Adding a table is a code
change.

**D7. CI runs `run_rba` after a deploy** (no `ci_auto_run: "false"`): the RBA
is free, two GETs.

## Probes

**P1. Serverless can download both files.** A one-time serverless job GETs
both files with `http_user_agent` and runs the parser on them. Pass: HTTP 200
for all four, 23, 17, 5 and 30 series, the first dates `03-Jan-2023`,
`04-Jan-2011`, `20-May-2013` and `31-Jan-1959`, and `FXRUSD`, `FIRMMCRTD`,
`FCMYGBAG10D` (10-year bond) and `FILRHLBVS` (standard variable housing rate,
owner-occupier) present. Fail (a block from the RBA's network): stop
and bring it to the user. Scripts and result in `references/poc/rba-rates/`,
row in `references/docs/registers/probes.md`.

**P1 result (2026-10-31): pass.** `references/poc/rba-rates/p1_download.py`
on serverless: HTTP 200 for all four files and the parser read them: F11.1
18,938 rows (21 series; AED and ZAR were discontinued in 2024 and have no
values since 2023), F1 46,902 (17), F2 16,298 (5), F5 7,824 (30). First dates
and the four named series as expected. A first run therefore writes 89,962
rows. Output in `p1_result.txt`.

## Dev results (2026-10-31)

`run_rba` as the service principal with `verify=true` (draft PR #123). The
table quota read 458/500 before the run.

- First run: success, both checks passed. `observations_raw`, Publish
  `observations_scd1` and Landing `silver_landing.rba__observations` each hold
  89,962 rows, 73 series, 4 tables, the same count as probe P1. `FXRUSD`
  (0.7040 on 30-Oct-2026), `FCMYGBAG10D` (5.208 on 28-Oct-2026) and `FILRHLBVS`
  (8.77 on 30-Sep-2026) are in Landing. `FIRMMCRTD`, the cash rate target, has
  no value on 30-Oct (F1's latest dates are still empty); its latest is 4.60
  on 29-Oct-2026.
- Second run: success, both checks passed. It wrote 845 rows (F1 228, F11.1 483,
  F2 110, F5 24), each table from about 31 days before its last stored date
  (29-Sep, 29-Sep, 28-Sep, 31-Aug). Raw grew to 90,807; Publish and Landing
  stayed at 89,962, as no new dates arrived and no value changed.
- Dates in Landing (user request before merge): `observation_date` and
  `publication_date` are DATE in `silver_landing.rba__observations`. Dev's
  Landing table had text dates, so the silver pipeline got one full refresh;
  it came back with 89,962 rows, 1959-01-31 to 2026-10-30, publication dates
  2026-10-08 and 2026-10-30, and `observation_date >= DATE'2026-10-28'` works.
  A third run of `run_rba` with `verify=true` succeeded. prd needs no refresh:
  its table is created with DATE columns on the first run.
- `reload=true` was not run in dev: it writes the same 89,962 rows again,
  which the first run already shows.
- The base address `.../csv` returns 403 in a browser (the server does not list
  its folder); every file under it returns 200.

## Risks / Trade-offs

- [The RBA changes the file layout] -> The parser fails on a missing
  `Series ID` row; the fetch task fails rather than writing bad rows.
- [Table quota] -> 12 slots take the count to about 470/500. Re-read it
  before the dev deploy; if it is above 488, stop and ask.
- [Revisions older than 31 days] -> Missed until `reload=true`. The RBA
  rarely revises these series.

## Migration Plan

1. iac `raw-volume-rba` applied (volume `bronze_rba.s3_raw`).
2. Probe P1.
3. Draft PR deploys to dev; `run_rba` as the service principal with
   `verify=true`, then again to check the incremental write.
4. Merge; CI runs `run_rba` in prd.

Rollback: remove the code; drop the three tables per target with approval.
