## 1. Sources (D1)

- [x] 1.1 FRED: add the 25 series (with `DTWEXBGS`) to `src/common/fred_series.py`; `RATES` rows in `src/common/investments.py` for them
      and for RBA `FCMYGBAG10D`; Yahoo benchmark row `DX-Y.NYB` in `data/portfolio/benchmarks.csv`. Check: unit tests
      of the rate list pass
- [x] 1.2 P1 in dev (draft PR deployed, one run at a time): `run_fred`, `run_portfolio`, `run_yahoo`. Check: FRED rows
      from the first dates in `p0_fred_series.txt` (`DTWEXBGS` from 2006); `DX-Y.NYB` prices from 1971

## 2. Silver (D2, D3)

- [x] 2.1 `src/common/currency.py` (`CURRENCIES`, `BASES`, `currency_value_sql()`) with unit tests (the CHF example)
- [x] 2.2 The indicator query generic over a list of series (`market_rate_indicator_sql.py`); the currency values and the
      added rates in `market_rate_indicator_daily`; column comments name the new series
- [x] 2.3 P2 before deploy: CHF in AUD by hand on one day; the inflation series unchanged (EXCEPT both ways)
- [x] 2.4 Silver verification: a cross value equals its two USD values; one row per series and trading day

## 3. Gold (D4)

- [x] 3.1 `src/common/currency_signals_sql.py` (rules in `currency.py`); `monitor_daily_signal` = union of three monitors;
      column comments name the currency values
- [x] 3.2 P3 before deploy on dev history: the dollar strong share per year (strong in 2022); the other monitors' rows
      unchanged (EXCEPT both ways)
- [x] 3.3 Gold verification: one row per currency, lens and day; the summary counts its rows

## 4. Dashboard and agent (D5)

- [x] 4.1 `common/currency_queries.py`, `common/currency_dashboard.py`, resource `resources/dashboards/currency_monitor.dashboard.yml`,
      `cicd/build_dashboards.py` and its test cover the new files
- [x] 4.2 Genie: instructions, examples, three benchmarks
- [x] 4.3 Every dashboard and agent query runs in dev

## 5. Run and check in dev

- [x] 5.1 `run_investments verify=true` in dev
- [x] 5.2 Genie benchmark evaluation in dev passes
- [ ] 5.3 P4: the user checks the dashboard and the agent; quota read (no change expected, 486)

## 6. After merge

- [ ] 6.1 prd: CI runs `fred`, `investments`, `portfolio`, `yahoo`; the user starts one more `run--investments--prd` so the
      dollar index reaches gold; prd matches dev for the latest day
- [ ] 6.2 The user checks the prd dashboard and agent
- [ ] 6.3 Planning: the story renamed Currency Monitor with an Analysis section; memory updated
