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

## One Silver Landing schema

Change `single-silver-landing-schema` (2026-10-30). Record: its `design.md` "Probes"; scripts in `references/poc/single-silver-landing-schema/`.

| Probe | Question | Result |
|---|---|---|
| P1 | Does a deployed pipeline accept a new default `schema:` and keep working? | Pass: `pipelines update` accepted it, the next update completed, the qualified-name table stayed with the same pipeline. |

## RBA rates

Change `rba-rates` (2026-10-31). Record: its `design.md` "Probes"; scripts in `references/poc/rba-rates/`.

| Probe | Question | Result |
|---|---|---|
| P1 | Can serverless download RBA tables F11.1, F1, F2 and F5, and does the parser read them? | Pass: HTTP 200 for all four; 18,938, 46,902, 16,298 and 7,824 rows; first dates and the named series as expected. |

## FRED rates

Change `fred-rates` (2026-10-31). Record: its `design.md` "Probes"; scripts in `references/poc/fred-rates/`.

| Probe | Question | Result |
|---|---|---|
| P1 | Can serverless call the FRED API with the key from the `fred` secret scope, and what do `series` and `series/observations` return for `DGS10`? | Pass: HTTP 200; 16,913 observations in one call from 1962-01-02 to 2026-10-29, 721 with the value `.`; `realtime_start/end` echo the request day; an unknown series is HTTP 400 with a JSON message. |
| P1b | Which FRED series is the Fed's policy rate, and how does it differ from `DGS10`? | Pass: `DFEDTARU` / `DFEDTARL` (target range, daily since 2008-12-16) were 4 / 3.75 on 2026-10-30, `DFF` (effective) 3.88, `FEDFUNDS` (monthly) 3.75; `DGS10`, the 10-year market yield, was 4.98. Different measures. |

## ISO market identifier codes

Change `iso-mic` (2026-10-31). Record: its `design.md` "Context"; scripts in `references/poc/iso-mic/`.

| Probe | Question | Result |
|---|---|---|
| P1 | What does the ISO 10383 CSV hold: key uniqueness, date format, rows per type and status? | Pass: 2,889 rows, `MIC` unique, 1,596 operating and 1,293 segment rows, 2,313 active, 574 expired, 2 updated; dates `YYYYMMDD`; country filled on every row. |
| P2 | What is the file's encoding, and which rows name an operating market that has no operating row? | UTF-8 without BOM, no charset in the header (`requests` would guess ISO-8859-1); 8 expired segments name a removed operating market, no operating row does. |

## Silver Domain: investments

Change `silver-domain-investments` (2026-10-31). Record: its `design.md` "Probes"; scripts in `references/poc/silver-domain-investments/`.

| Probe | Question | Result |
|---|---|---|
| P1 | For each current S&P 500 CIK, which new concepts appear in a 10-K ending in the last 18 months? | Pass: of 500, `Liabilities` 358, `AssetsCurrent` 417, `PreferredStockValue` 219, earnings per share 480; the liabilities fallback inputs exist for 139 of the 142 without `Liabilities`. |
| P2 | Which market does each current S&P 500 symbol trade on, per SEC `company_tickers_exchange.json` and per Yahoo? | Pass: both cover all 503 and agree on every one: 345 `XNYS`, 157 `XNAS`, 1 `XCBO`; Yahoo is the chosen source (no new table). |

## world-indexes (exploration, before a proposal)

Scripts and results in `references/poc/world-indexes/`.

| Probe | Question | Result |
|---|---|---|
| P1 | Does Yahoo serve a daily price series for one index per major exchange? | 31 of 36 symbols return full history to 2026-10-30 (e.g. `^GSPC` from 1927, `^N225`, `^FTSE`, `^HSI`, `^BVSP`, `^AXJO`, `^NZ50`, `FTSEMIB.MI`). Failed or nearly empty: Saudi `^TASI.SR` (1 row), Thailand `^SET.BK` (1 row), Russia `IMOEX.ME` (empty), Sweden `^OMXS30` (empty); Argentina `^MERV` stops on 2026-10-16 and has no currency. Index volume is 0 on many days. |
| P2 | Are there other Yahoo symbols for those five gaps? | Sweden `^OMX` works (from 2008). Saudi, Thailand, Argentina only through USD ETFs (`KSA`, `THD`, `ARGT`) or one stock (`2222.SR`); Russia has nothing current (`MOEX.ME` stops 2026-07-09 with no close). |

## macro-prices (exploration, before a proposal)

Daily gold and commodity prices, US and Australian CPI (2026-11-02). Scripts and results in `references/poc/macro-prices/`.

| Probe | Question | Result |
|---|---|---|
| P1 | Which Yahoo symbols give daily gold and commodity prices, and does their exchange map to a market? | CRB is `^TRCCRB` (from 1994, exchange `FGI`); `^CRB` and `^BCOM` fail. Daily: `GC=F`, `SI=F`, `HG=F` (`CMX`), `CL=F` (`NYM`), `^SPGSCI` (`SNP`), all from 2000 or earlier. ETFs `GLD`, `IAU`, `DBC`, `GSG` map to `XNYS` (`PCX`); `CMX`, `NYM`, `FGI`, `SNP` are not in `YAHOO_EXCHANGE_TO_MARKET`. |
| P2 | What do the FRED US CPI series hold? | `CPIAUCSL` (from 1947), `CPIAUCNS` (from 1913), `CPILFESL` (from 1957): monthly, dated the 1st of the month, last 2026-09-01. |
| P3 | What does RBA table G1 hold, and does the RBA parser read it? | Quarterly only (CPI index `GCPIAG`, base Sep 2025 month = 100, and four year-ended % series), from 1922, dated the quarter's last day as `30/09/2026`, with empty future rows. `parse_table` fails: it expects `03-Jan-2023` dates. |
| P4 | Does the ABS Data API (no key) serve the complete monthly CPI? | Yes, dataflow `ABS,CPI,2.0.0`, key `MEASURE.INDEX.TSEST.REGION.FREQ`: monthly all groups Australia `1.10001.10.50.M` from 2024-04 only (30 rows to 2026-09); quarterly `1.10001.10.50.Q` from 1948-Q3. No seasonally adjusted monthly series under `TSEST` 20. Structure URLs take `/ABS/CPI/2.0.0`, data URLs `ABS,CPI,2.0.0`. |
| P5 | Do the 8 commodity symbols get through the Yahoo fetch's own steps (bulk prices, actions, calendar, options)? | Pass for all 8 (`^TRCCRB`, `^SPGSCI`, `GC=F`, `SI=F`, `HG=F`, `CL=F`, `DBC`, `GSG`): prices and a calendar row with the exchange code; the calendar call prints "No fundamentals data found" and returns empty (as for `^VIX`). Only `DBC` and `GSG` have options; `DBC` has 9 events. `XNYM` and `XXXX` ("NO MARKET (E.G. UNLISTED)") are rows of `silver_domain_investments.market`. |
| P6 | Does `yf.download` with `start=1970-01-01`, as the fetch calls it, return each new commodity symbol's full history? | Pass: `^SPGSCI` 10,792 rows from 1984-01-03, `^TRCCRB` 8,174 from 1994-01-03, `GC=F`/`SI=F`/`HG=F` about 6,570 from 2000-08-30, `CL=F` 6,577 from 2000-08-23, `DBC` 5,218 from 2006-02-06 (9 distributions), `GSG` 5,103 from 2006-07-21; about 53,000 rows in all. |
| P7 | Do P4's two ABS CPI series requests work from serverless? | Yes, both 200 in 0.3 s: `1.10001.10.50.Q` 313 rows (1948-Q3 to 2026-Q3, last 103.64, 59 KB) and `1.10001.10.50.M` 30 rows (2024-04 to 2026-09, last 104.34, 6 KB). No empty `OBS_VALUE`. The label columns `Measure`, `Index`, `Adjustment Type`, `Region`, `Frequency`, `Unit of Measure`, `Reference Base Period` are present (base `Sep 2025 = 100.0`). |

## neon-clickstream-to-patterns

neon and clickstream moved to the patterns bundle (2026-11-04). Scripts and logs in `references/poc/table-cleanup/`.

| Probe | Question | Result |
|---|---|---|
| P1 | Do the neon and clickstream pipelines run from the patterns bundle as the human, and pass their verify jobs? | Yes (`neon-clickstream-to-patterns`, 2026-11-04): neon seed 200/50/500/1,240, Lakeflow Connect through `neon_dev` as the human, counts equal Neon's; clickstream batch 3 with a new field absorbed, 800 rows, 600 with `device_type`. Nine slots used (483 to 492). |
| P2 | What does `bundle destroy` of the patterns bundle leave behind? | 19 resources deleted. The Lakeflow Connect tables go with their pipeline but their hidden `__materialization_mat_*` twins stay; the Auto Loader table and its twin stay. Dropped with approval; `references/poc/table-cleanup/` has the scripts and logs. |

## market-climate (story probes, before change 1)

10-year inflation-adjusted P/E with real data (2026-11-04). Notebook, scripts and results in `references/poc/market-climate/`.

| Probe | Question | Result |
|---|---|---|
| P1 | Does the 10-year inflation-adjusted P/E give sensible values from our tables? | Yes: Apple's 10 10-Ks, CPI and factors give a 10-year average of 90.82 bn in today's money, P/E (10-year) 54.4 against trailing 38.3; the index (458 members) gives P/E (10-year) 40.8 and trailing 24.7, close to published CAPE in late 2025. History empty (see P2). |
| P2 | Why is P1's history empty, and why do some members have no market value? | Prices start 2025-10-28 for every member and SPY (a new symbol loads 365 days). 42 members have no cover share count on their latest filing (24 had one on an older filing); VYLR has no SEC data. Median member has 16 years of 10-Ks; 444 of 503 have a year end by 2016. |
| P3 | Why do share-class companies have no share count? | SEC sent no share facts for the latest filings of MA, NKE, UPS, FOXA, HSY; their last cover totals are from 2010 (MA, UPS), 2015 (NKE), 2019 (FOXA). HSY's `CommonStockSharesOutstanding` is one class only. Company facts leave out per-class values. |
| P4 | Does SEC report weighted average basic shares for them? | Yes, current to 2026: MA 883 m, NKE 1.48 bn, UPS 850 m, FOXA 421 m, GOOGL 12.17 bn, AAPL 14.66 bn; not HSY (stops 2015). |
| P5 | After `shares-outstanding-all-classes`, how many index members still have no share count? | 8 of 500 (dev, 2026-11-04; was 42): ARES, BRK.B, ERIE, HSY, STZ, TSN, V and VYLR (no SEC data). 459 have a cover count, 485 a weighted average, 492 either. MA 875 m, NKE 1.48 bn, UPS 851 m, FOXA 421 m. GOOGL's two counts (12.29 bn cover, 12.26 bn average) agree. |

## market-climate-silver

Column descriptions on materialized views (2026-11-04, dev, throwaway pipeline). Script and result in `references/poc/market-climate-silver/`.

| Probe | Question | Result |
|---|---|---|
| P1 | Can `@dp.materialized_view(schema=...)` describe only some columns? | No: a partial `schema=` fails ("user-specified schema that is incompatible with the schema inferred from its query"). Listing every column with a `COMMENT` works and the comments reach Unity Catalog. || P2 | Do the new silver columns give the expected values in dev? | Yes (2026-11-04): Apple's FY2025 10-K row has 10 years, CPI 324.8, plain average 76.35 bn and inflation-adjusted 87.55 bn, equal to the story probe's figures; its FY2026 row (filed 2026-11-03) 84.99 / 97.66 bn at CPI 336.94. 444 of the current rows have 10 years. A period ending 2025-10-31 uses CPI 324.8 (September, October has no value). `^GSPC`: 14,332 rows from 1970-01-02 to 2026-11-03, close 7,568.92 above its 200-day average 7,315.89, slope +1.10%. |

## market-climate-gold

The gold queries and tables with real data (2026-11-04, dev). Scripts and results in `references/poc/market-climate-gold/`.

| Probe | Question | Result |
|---|---|---|
| P1 | Does the valuation query give sensible figures? | Yes: 256 days from 2025-10-28; on 2026-11-03 489 of 500 members used (8 without a share count, 52 with fewer than 10 years), market value 66.5 tn, trailing P/E 24.4, plain 10-year 47.1, inflation-adjusted 10-year 40.0. The story probe (2026-11-02, 458 members) had 40.8 and 24.7. |
| P2 | Do the signals follow the rules? | Yes: no light disagrees with its yes count; the 2022-2023 Fed hike run is 2022-03-17 to 2024-01-26 (last hike 2023-07-27 plus 6 months). Found: the Fed series lags a few days, so the answer uses the latest observation up to 7 days old; climate rows then reach the last valuation day. |
| P3 | What do the built tables hold? | 256 valuation rows; signals from 1970 (trend), 2008-12 (Fed), 2025-10-28 (valuation, climate). Latest day red (sell) in both lenses, 3 of 3 yes. Over the 256 days both lenses are red on 243 days and yellow on 13: the 10-year ratio stays above 30. |
| P4 | Are the tags and descriptions in Unity Catalog? | Yes: `design_pattern = gold_materialized_view_sql` on both tables; 16 of 16 and 15 of 15 columns described. |

## market-climate-dashboard

The member valuation table, the renames and the dashboard queries (2026-11-05, dev). Scripts and results in `references/poc/market-climate-dashboard/`.

| Probe | Question | Result |
|---|---|---|
| P1 | Do the new queries and then the new tables equal the old tables? | Yes, both times: valuation 256 rows and signals 38,286 rows, no row only in one side, every `ingested_timestamp` equal. Old tables and their hidden copies dropped in dev afterwards (approved). |
| P2 | Does the member query give sensible figures? | Yes: 128,000 rows (500 members x 256 days); on 2026-11-03 489 used, 7 `no_share_count`, 2 `no_net_income`, 1 `no_filing`, 1 `no_ten_year_average`; Nvidia pushes the P/E up most (+2.38), JPMorgan Chase down most (-0.62). |
| P3 | Does every dashboard dataset query run with the dashboard's catalog and schema defaults? | Yes, all 17, with the date and sector parameters bound; silver tables are reachable by two-part name. Latest day member sums equal the index row (differences 0.00). |
| P4 | Can the CI principal deploy a dashboard? | Yes with the warehouse id; a lookup by name fails (`databricks-sql-access` entitlement missing for the principal, 403 on listing warehouses). A dashboard created with `--json` shows no dataset catalog. |

## market-climate-genie

The Genie agent as code (2026-11-05, dev). Scripts and results in `references/poc/market-climate-genie/`.

| Probe | Question | Result |
|---|---|---|
| P1 | Can the CI principal deploy a `genie_spaces` resource, and is `${var.catalog}` filled in inside `serialized_space`? | Create: yes (agent made on `c36e1ff0d4e62a24`, table `mdp_dev.gold_analytics_gateway.monitor_daily_signal`, `users` `CAN_RUN`). The next deploy FAILS at planning: reading the agent returns 403 `You need the aclPath entitlement: /sqlanalytics` because the principal has only `workspace-access`. Needs `databricks-sql-access` on the principal: granted by iac `cicd-sp-sql-access` (PR #83, applied 2026-11-05); after it the redeploy passes and the agent shows all five tables, 13 examples, 3 joins, 6 benchmarks. The API joins the `content` array with no separator, so each instruction line ends with a line break. A resource key must be unique across resource types (`market_climate_genie`, not `market_climate`). |
| P2 | Does every example and benchmark SQL of the agent run in dev with the catalog filled in? | Yes, all 13 examples and 6 benchmarks (`p2_result_dev.txt`). Latest day 2026-11-03: both lights red 3/3, index P/E 40.0458, EQT 749.74 against 12.78 trailing, 11 members left out. |
| P3 | Does Genie's own benchmark evaluation pass in dev? | First run 5 of 6: "Why is EQT's P/E so high?" was marked missing columns because Genie answered with the step-by-step table (right numbers, different shape) and the expected SQL wanted four columns in one row. The benchmark now asks for the two P/E figures; the explanation is left to the user check (P4). Second run 6 of 6 (`p3_eval_results_dev_run2.json`). |

## inflation-deflation-monitor

The inflation/deflation stars and their silver inputs (2026-11-05). Scripts and results in `references/poc/inflation-deflation-monitor/`.

| Probe | Question | Result |
|---|---|---|
| P1 | Does dev get the full history of the eight commodity benchmarks? | Not at first: `reload_symbols` restarted from the symbol's first stored day (2025-11-03 in dev), so nothing changed. After `plan()` loaded all history for a reloaded benchmark, the second run gave dev the same first dates as prd (1984 `^SPGSCI`, 1994 `^TRCCRB`, 2000 futures, 2006 funds), one day more recent data than prd. |
| P2 | Does the `market_rate_indicator_daily` query give the right figures? | Yes, on dev: the Fed 200-day average on 2026-09-30 equals a hand average (3.646350); the CPI change for September 2026 is 0.585110 on every day until the next reading; the real rate equals its two parts. The first hand check differed because FRED had no reading yet for 2026-10-30 (the query carries the last one). The 52-week window gives EQT 68.239998 and 47.939999, as the dashboard. |
| P3 | What ratings does the rule give over prd history? | About 250 rated days a year from 2001-06-18 (limited by gold futures, which start 2000-08), not 1994 as expected. Few deflation days: 4 days in 2015 and none in 2009 (the commodity and gold stars were on). 2004-2006 and 2010 mostly 3-4 stars. The monthly CPI change must be exempt from the 7-day age rule (the first run kept only 36 days a year). Latest day 2026-11-03 on prd data: 3 stars (commodities, consumer prices, interest rates on, gold off), Inflation Danger. |
| P4 | Do the dashboard and agent queries run, and does the agent pass its benchmarks in dev? | All 34 dashboard dataset queries (22 Market Climate, 12 Inflation-Deflation Monitor) and all 30 agent example and benchmark queries run on dev (`p4_dashboard_queries_dev.txt`). The first benchmark evaluation was 8 of 9: "How many inflation stars are on today?" got the right count (3) but the expected SQL returned two columns; narrowed to the count, the next run was 9 of 9 (`p3_eval_results_dev_run4.json`). Dev after `run_investments verify=true`: rating 3 (Inflation Danger) on 2026-11-03, the same as the prd-history probe; market climate rows unchanged (plus one new day); EQT 52-week figures unchanged (68.24, 47.94); table quota 484. |
