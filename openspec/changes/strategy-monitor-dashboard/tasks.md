## 1. States (D1)

- [ ] 1.1 `strategy_states_query` in `src/common/strategy_events_sql.py`; the events query reads it; tests
- [ ] 1.2 Probe: the events query output on dev is identical before and after the split (EXCEPT both ways = 0 rows)

## 2. Dashboard (D2-D4)

- [ ] 2.1 `src/common/strategy_queries.py` (datasets of the three pages) and `src/common/strategy_dashboard.py` (pages,
      parameters, filters); resource `resources/dashboards/strategy_monitor.dashboard.yml`; `cicd/build_dashboards.py` entry;
      generated file and its equality test
- [ ] 2.2 Every dataset query runs on dev (`p3_test_queries.py` includes the strategy datasets)

## 3. Genie (D5)

- [ ] 3.1 `GOLD_TABLES`, instructions, examples and the four benchmarks; generated agent file
- [ ] 3.2 Every example and benchmark SQL runs in dev

## 4. Run and check in dev

- [ ] 4.1 Draft PR deployed (dashboard and agent in dev); benchmark evaluation in dev passes
- [ ] 4.2 The user checks the dev pages and agent; quota read (488, no change)

## 5. After merge

- [ ] 5.1 prd: CI deploys; dashboard queries run on prd; benchmark evaluation on prd; the user checks prd
- [ ] 5.2 Archive; planning design status; memory
