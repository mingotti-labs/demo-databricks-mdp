## 1. Dev data (D1)

- [x] 1.1 P1: `cicd/run_dev.py yahoo --param reload_symbols=^TRCCRB,^SPGSCI,GC=F,SI=F,HG=F,CL=F,DBC,GSG`, then
      `cicd/run_dev.py investments`. Check: first price dates of the eight in dev equal prd (1994, 1984, 2000, 2006)

## 2. Silver (D3, D4)

- [x] 2.1 `common` query for `market_rate_indicator_daily` and the pipeline file with every column described
- [x] 2.2 52-week high and low columns on `price_indicator_daily`, described
- [x] 2.3 P2 before deploy: the effective rate's average on one date against a hand average; the CPI change for
      September 2026 is 0.585 and the CPI index is carried to every date; EQT's 52-week high and low are 68.24 and 47.94 on 2026-11-03
- [x] 2.4 Silver verification gains: one row per series and `^GSPC` date; the real rate equals its two parts

## 3. Gold (D5)

- [x] 3.1 `common/inflation.py` (thresholds, labels) with unit tests, `common/inflation_signals_sql.py`
- [x] 3.2 `monitor_daily_signal` = union of both monitors; column comments name the new values
- [x] 3.3 P3 before deploy on prd history: ratings per year, -1 in 2009, mostly 3-4 in 2021-2022; market climate rows
      unchanged (EXCEPT both ways)
- [x] 3.4 Gold verification gains: five rows per day for the monitor; rating equals stars on, -1 only with CPI 12-month below 0

## 4. Dashboard and Genie (D6, D7)

- [ ] 4.1 `common/dashboard_widgets.py` from `market_climate_dashboard.py`; Market Climate JSON unchanged
- [ ] 4.2 `common/inflation_queries.py`, `common/inflation_dashboard.py`, resource
      `resources/dashboards/inflation_deflation.dashboard.yml`; `ds_company_figures` reads the stored 52-week columns;
      `cicd/build_dashboards.py` (and its `--check` test) writes all generated files
- [ ] 4.3 Genie agent: tables, instructions, examples, benchmarks (D7)
- [ ] 4.4 Every dashboard and Genie query runs in dev (probe script)

## 5. Run and check in dev

- [ ] 5.1 Draft PR deploy-dev; `run_investments verify=true`
- [ ] 5.2 Genie benchmark evaluation in dev passes
- [ ] 5.3 P4: the user checks the dashboard and asks the agent; quota read (expected 484 after dev)

## 6. After merge

- [ ] 6.1 prd: CI runs `investments`; prd ratings match dev for the latest day; quota read (expected 486)
- [ ] 6.2 The user checks the prd dashboard and agent
- [ ] 6.3 Planning: the story gets its Analysis section; memory updated
