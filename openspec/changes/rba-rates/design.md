## Context

See proposal.md. The two RBA files share one layout, checked 2026-10-31:

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

F11.1 has 23 series and about 2,170 dates (from 03-Jan-2023); F1 has 17 series
and about 4,000 dates (from 04-Jan-2011). Recent F1 dates leave most cells
empty until the RBA fills them. The files start with a byte order mark.
Exchange rates before 2023 are only in Excel files (`f11hist.xls`,
`f11hist-1969-2009.xls`).

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

**D1. One long table for both RBA tables.** Rows are
`(table_id, series_id, observation_date, value)` plus the series metadata.
Two tables per RBA table would double the slots (24 instead of 12) for no
query gain: every consumer filters by `series_id`. Rejected: one wide table
per RBA table (series as columns), which breaks when the RBA adds a series.

**D2. The fetch writes long JSON Lines, not the CSV.** The header rows are
not data, so Auto Loader cannot read the CSV as it is. The fetch parses it in
`src/common/rba_tables.py` (pure functions, unit tested) and writes one file
per table per run to
`/Volumes/<catalog>/bronze_rba/s3_raw/observations/landing/<table_id>/<UTC stamp>.jsonl`.
Values stay text as the RBA wrote them, including the date (`03-Jan-2023`).
`ingested_timestamp` is the fetch time, written into every row (one value per
file), as SEC and Yahoo.

**D3. Write only the last 31 days after the first run.** The fetch reads the
last stored date per table from `bronze_rba.observations_raw` and writes rows
dated from 31 days before it. That keeps late-filled F1 cells and short
revisions, and keeps raw growth to about 1,200 rows a run. An empty raw table
or `reload=true` writes every row. Rejected: writing the whole file each run
(about 120,000 rows a week, almost all repeats).

**D4. Publish is SCD1 by `(series_id, observation_date)`**, sequenced by
`ingested_timestamp`: the latest value wins, and a revision is an update.
History of revisions stays in raw. Same pattern as Yahoo's prices.

**D5. Silver Landing `silver_landing.rba__observations`** through
`land_changes`, keyed by `series_id` and `observation_date`.

**D6. Table list in code.** `rba_tables.py` holds
`TABLES = {"F11.1": "f11.1-data.csv", "F1": "f1-data.csv"}`; the bundle
variable `rba_tables_url` holds the base address. Adding a table is a code
change.

**D7. CI runs `run_rba` after a deploy** (no `ci_auto_run: "false"`): the RBA
is free, two GETs.

## Probes

**P1. Serverless can download both files.** A one-time serverless job GETs
both files with `http_user_agent` and runs the parser on them. Pass: HTTP 200
for both, 23 and 17 series, the first dates `03-Jan-2023` and `04-Jan-2011`,
`FXRUSD` and `FIRMMCRTD` present. Fail (a block from the RBA's network): stop
and bring it to the user. Scripts and result in `references/poc/rba-rates/`,
row in `references/docs/registers/probes.md`.

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
