## 1. Rules and query (D1, D3)

- [ ] 1.1 `src/common/strategy.py`: `SETUP_DOWN_WEEKS = 3`; `short_selling_setup` needs the streak; tests
- [ ] 1.2 `src/common/strategy_events_sql.py`: the short selling `is_setup_on` condition and the reason texts; tests of the text
- [ ] 1.3 Column descriptions of `strategy_daily_event` (`event_code`, `down_week_count`) say the setup needs the streak
- [ ] 1.4 Gold verification: a short selling `setup_start` has `down_week_count` of at least 3 and price-to-sales above 15

## 2. Run and check in dev

- [ ] 2.1 Draft PR deployed; `run_investments verify=true`
- [ ] 2.2 Dev counts equal probe P11 for 3 weeks (setup starts 47 and entries 2 on prd data up to 2026-11-06; dev may differ by the latest day); no quota change (488)

## 3. After merge

- [ ] 3.1 prd: CI runs `investments`; the table equals dev
- [ ] 3.2 Archive; planning: design rules section; memory
