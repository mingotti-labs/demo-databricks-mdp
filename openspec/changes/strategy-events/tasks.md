## 1. Rules and query (D1-D6)

- [ ] 1.1 `src/common/strategy.py`: codes, names, thresholds (2.5%, 5%, five weeks, six weeks, price-to-sales 15),
      column descriptions; unit tests
- [ ] 1.2 `src/common/strategy_events_sql.py`: weeks, week states, events per strategy, union; unit tests of the text
      (keys, thresholds present)
- [ ] 1.3 Probe P5 before deploy (prd, read only, the same text): event counts per strategy and code; 001 matches P1
      (14 setup weeks grouped into periods, no entry); 002 candidates with price-to-sales above 15

## 2. Table

- [ ] 2.1 `src/layers/gold/analytics_gateway/strategy_daily_event.py` (materialized view, described columns)
- [ ] 2.2 Gold verification: key unique; every `entry` inside a setup period; every `setup_end` after its `setup_start`

## 3. Run and check in dev

- [ ] 3.1 Quota read (484 expected); draft PR deployed; `run_investments verify=true`
- [ ] 3.2 Dev counts equal P5's shape; quota read (488 expected)

## 4. After merge

- [ ] 4.1 prd: CI runs `investments`; counts compared with dev
- [ ] 4.2 Archive; memory updated; then propose change 3 (`strategy-monitor-dashboard`)
