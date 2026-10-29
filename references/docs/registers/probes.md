# Probes Register

A probe is a small throwaway experiment, run in dev before a design depends on
an assumption: what it asks, how it was run, what it showed. Each change records
its probes in its own `design.md`; this register lists them all in one place, so
a later change can find out what is already known instead of asking again.

**How to add one**: when a change runs a probe, add a row here in the same PR
that records its result in the change's `design.md`. A probe that failed or
disproved the plan belongs here too; those are the useful ones.

**Method**: a scratch pipeline or notebook in dev, usually on a copy of real
tables in the dev-only `pattern_bronze_publish` schema (or `zz_` tables), the
production code untouched. Scratch objects are dropped afterwards, with approval.

**Result**: *pass* (the assumption held), *pass with a constraint*, *fail*
(the design changed), *probe error* (the experiment was wrong, not the idea).

## Moving tables between pipelines

Change `acnc-two-pipelines` (2026-10-19). Record: its `design.md` "Probes".

| Probe | Question | Result |
|---|---|---|
| P1 | Does moving an Auto CDC SCD2 target (with a closed version) to another pipeline with `ALTER STREAMING TABLE ... SET TBLPROPERTIES('pipelines.pipelineId'=...)` keep its history? | Pass. Rows and closed versions unchanged; an unchanged rerun adds no version; one changed key adds exactly one. |
| P2 | What happens if the old pipeline still defines the table and runs after the move? | Pass (safe failure): `Table ... is already managed by pipeline <destination>`; nothing harmed. |
| P3 | Does deleting the emptied source pipeline keep the moved tables? | Pass with a constraint: tables stay, but `bundle deploy` refuses to delete a pipeline without `--auto-approve`, so delete it before the PR merges. |
| P4 | Does a two-part `name="schema.table"` resolve, and an in-pipeline read of another schema's dataset? | Pass. |
| P5 | Does `pipelines.reset.allowed=false` stop a full refresh from truncating an SCD2 table? | Pass: the full refresh is refused, a normal update runs, history kept. |

## Tagging tables with their design pattern

Change `design-pattern-table-tags` (2026-10-22).

| Probe | Question | Result |
|---|---|---|
| P1 | Can the run-as principal `ALTER STREAMING TABLE ... SET TAGS` with no `APPLY TAG` grant? | Pass. |
| P2 | Do the tags survive the next pipeline refresh? | Pass. |

## Timestamps stamped only on changed rows

Change `correct-platform-timestamps` (2026-10-22 to 10-23). Record: its archived `design.md`.

| Probe | Question | Result |
|---|---|---|
| P1 | When a dataset is removed from a pipeline's code, is its table dropped? | Pass: the table stays with its rows, still tied to the pipeline, so a migration must copy it out. |
| P2 | Does a null-safe SCD2 `MERGE` write only changed rows? | Pass: two unchanged runs wrote 0 rows (snapshot Auto CDC rewrote 65,907 current rows); a change closed one version and inserted one. Later retired. |
| P3 | Does a full rebuild that compares with the previous table keep `transformed_timestamp` on unchanged rows? | Pass. Now the Silver Normalised standard (`rebuild.py`). |
| P4 | Does Silver Landing read only changed rows from the SCD2 table's change feed? | Pass: Landing equals a full read; only changed rows are restamped. |
| P5 | Does standard snapshot Auto CDC without `ingested_timestamp` write 0 rows on an unchanged load? | Pass. This is the bronze full pattern. Root cause of the original bug: that per-load column passed in as untracked. |
| P6 | Can a function source pass raw's exact fetch time as the snapshot version? | Pass in the probe (version must be cut to the millisecond), **unusable in the real pipeline**: a function source cannot read a dataset defined in its own pipeline (`REFERENCE_DLT_DATASET_OUTSIDE_QUERY_DEFINITION`). The probe's raw lived outside the pipeline, which hid it. |
| P7 | Does Landing from the P5 table's change feed get only changed rows? | Pass. |
| P8 | Can streaming Auto CDC read raw? | Fail by design: a materialized view cannot be streamed (`STREAMING_FROM_MATERIALIZED_VIEW`). |

**Lesson from P6**: probe the real shape. A probe whose inputs differ from the
production pipeline's (here: raw inside or outside the pipeline) can pass for
the wrong reason.

## Rolling the pattern out

Change `rollout-bronze-full-pattern` (2026-10-23).

| Probe | Question | Result |
|---|---|---|
| P1 | Is `delta.enableChangeDataFeed` applied through `table_properties` to an SCD2 table that already exists and is pipeline-owned (ungm)? | Pass: the property is set, and Landing loaded every row once. |
| P2 | Does iso's deduplicated view, without the stamp, write 0 rows on an unchanged second load? | Pass. |

## Landing from an SCD1 table

Change `refactor-airroi-clickstream-neon` (2026-10-23).

| Probe | Question | Result |
|---|---|---|
| P1 | Does the change feed of an Auto CDC SCD1 target feed a Landing streaming table (inserts and updates, nothing on an unchanged run)? | Pass: 600 rows loaded; a new event gave 1 insert and a re-sent event 1 update in both tables; Landing equals SCD1; only changed rows were restamped. A first attempt looked like a failure and was a probe error: the raw `timestamp` is a string with a `T` separator, and my edited value (space separator) sorted as older. |

## Moving tables from a human pipeline to the service principal

Change `dev-runs-as-service-principal` (2026-10-29). Record:
`references/poc/pipeline-ownership/README.md` (scripts and data alongside).

| Probe | Question | Result |
|---|---|---|
| O1 | Can the human (workspace admin, table and catalog owner) move a table from its own pipeline to the SP's? | Fail: `DESTINATION_PIPELINE_PERMISSION_DENIED`; one identity must own and run both pipelines. |
| O2 | Can the human run a job as the SP (`run_as`)? | Fail: needs `servicePrincipal.user` on the SP. |
| O3 | Can a pipeline's owner be changed to the SP? | Fail: `Only metastore admins can change pipeline owner`; the metastore owner is `System user`. |
| O4 | Does deleting a pipeline drop its tables? | No: the tables stay, pointing at the deleted id (regular pipelines, five times). |
| O5 | Does a new pipeline adopt the left-behind tables? | No: `already managed by pipeline <deleted id>`. |
| O6 | After the source is deleted, does the move work, and does a moved Auto Loader table keep its checkpoint? | Pass: only the destination's owner is checked; rows and SCD1 state kept, only the new file read. |
| O7 | Can a pipeline table be handed over with `OWNER TO`? | Fail: `CHANGE_OWNER_NOT_ALLOWED_FOR_PIPELINE_TABLE`; the owner follows the pipeline's run-as. |
| O8 | With the human pipeline deleted and the SP granted `ALL PRIVILEGES, MANAGE`, can the SP move the tables to its own pipeline? | Fail: `User is not an owner of Pipeline '<deleted human pipeline>'`. No human-to-SP move without a reload; dropping and replaying the volume restored Yahoo bronze with identical counts. |

## Dividend portfolio sources

Change `dividend-portfolio-probes` (2026-10-25). Record: its `design.md`
"Probe results". Scripts: `references/poc/dividend-portfolio/`.

| Probe | Question | Result |
|---|---|---|
| P1 | Can serverless reach Wikipedia, FMP, SEC, Yahoo, RBA and FRED? | Pass: every host answered. |
| P2 | How many tables does the metastore hold? | Pass: 301 (272 in `mdp_dev`/`mdp_prd`, 28 in `samples`); about 200 to 230 left. |
| P3 | Can the Wikipedia S&P 500 page be parsed? | Pass with a constraint: 503 rows, 500 CIKs, every date added parses; read CIK as text; `BRK.B` uses a dot; the changes table is gone from the page. |
| P4 | Does the FMP free plan give the S&P 500 list and dividend pay dates? | Fail: the list is paid (402), dividends only for some symbols (KO yes, O and BRK-B refused), calendar with a date range paid. FMP dropped from version one. |
| P4b | Is the FMP dividends calendar free without a date range? | Fail for the story: 44 symbols only, the free sample. |
| P5 | Do SEC company facts cover the ranking's figures? | Pass with constraints: concepts vary by company and over time (take the latest fiscal year); banks, insurers and REITs lack some figures; XOM's ticker and CIK now point to a new holding company with no 10-K, history under the old CIK. |
| P6 | Does `yfinance` fetch the whole index from serverless? | Pass: 503 tickers, no blocking; 1-year prices in one bulk call (54 s), full dividends (142 s), options for 502 (36 s). |
| P6b | Does `yfinance` give dividend pay dates? | Pass: `Ticker.calendar` has the next pay date for 413 of 420 payers, matching FMP for KO and JNJ; only the next one, so history builds weekly. |
| P7 | What do SEC company facts look like in long form for the mapped concepts? (change `sec-company-facts`, its P1) | Pass: about 2,250 rows and 600 KB per company, 1.14 million rows and 313 MB for 505; `cik, taxonomy, concept, unit, accn, start, end` is unique; `start` empty on point-in-time values. |
| P8 | What do Yahoo prices, dividends, calendar and options look like for 20 symbols? (change `yahoo-market-data`, its P1) | Pass with a constraint: keys `symbol, date` and `symbol, ex_date` unique; calendar gives `Dividend Date` and `Ex-Dividend Date`; ETFs have no calendar; option open interest is 0 on every strike (even AAPL) while volume is filled in, so volume is the activity measure. |
| P8b | Does the incremental Yahoo fetch work: only new days, a manual reload, resuming a repaired run? (change `yahoo-market-data`, its P2) | Pass: second run 1,034 price rows (two days per symbol), no calendar version; `reload_symbols=AAPL` reloads 252 days and AAPL's events; a run cancelled after 100 symbols and repaired keeps `{{job.run_id}}` and fetches only the other 417. |
