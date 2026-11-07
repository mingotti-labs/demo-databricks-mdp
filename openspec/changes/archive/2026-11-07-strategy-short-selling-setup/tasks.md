## 1. Rules and query (D1, D3)

- [x] 1.1 `src/common/strategy.py`: `SETUP_DOWN_WEEKS = 3`; `short_selling_setup` needs the streak; tests
- [x] 1.2 `src/common/strategy_events_sql.py`: the short selling `is_setup_on` condition and the reason texts; tests of the text
- [x] 1.3 Column descriptions of `strategy_daily_event` (`event_code`, `down_week_count`) say the setup needs the streak
- [x] 1.4 Gold verification: a short selling `setup_start` has `down_week_count` of at least 3 and price-to-sales above 15

## 2. Run and check in dev

- [x] 2.1 Draft PR deployed; `run_investments verify=true`
- [x] 2.2 Dev counts equal probe P11 for 3 weeks (setup starts 47 and entries 2 on prd data up to 2026-11-06; dev may differ by the latest day); no quota change (488): dev shows 47 setup starts, 45 ends and 2 entries as in P11; TSLA's 2026-10-30 start is gone

## 3. After merge

- [x] 3.1 prd: CI ran `investments` (success); the table equals dev: strategy 001 6/5/1, strategy 002 47/45/2, all columns described (`p12_strategy_table_dev_prd_3weeks.txt`)
- [x] 3.2 Archive; planning: design rules section; memory
