## 1. Member table

- [x] 1.1 `common/market_climate_sql.py`: `index_member_valuation_query()` (D2) and
      `index_valuation_query(member_source)` summing it (D3)
- [x] 1.2 `src/layers/gold/analytics_gateway/valuation_daily_index_member.py` with full described schema (D6)

## 2. Renames

- [x] 2.1 `valuation_daily_index.py` (from `index_valuation_daily.py`), reading the member table
- [x] 2.2 `monitor_daily_signal.py` (from `monitor_signal_daily.py`), reading `valuation_daily_index`
- [x] 2.3 Every reader of the old names: signals query default, verification, probes scripts, CLAUDE.md,
      NAMING.md (rule D1), `design-patterns.md`

## 3. Verification

- [x] 3.1 `verify_gold_market_climate.py` on the new names, plus: member key unique; a member row for every
      current member and day; member sums equal the index row (counts exact, amounts to the cent);
      "without" ratio recomputes for the top member of the latest day

## 4. Dashboard

- [x] 4.1 Probe P2 (date parameter defaulting to latest) and P3 (every dataset query by CLI), saved in
      `references/poc/market-climate-dashboard/`
- [x] 4.2 `resources/dashboards/market_climate.dashboard.yml` and `src/dashboards/market_climate.lvdash.json`:
      pages Climate, Climate Deep Dive, Sector Deep Dive (D5)

## 5. Run and check in dev

- [x] 5.1 Draft PR deploy-dev; `run_investments verify=true` (polled)
- [x] 5.2 P1: old vs new tables equal in dev (record as a probe)
- [x] 5.3 Drop dev `index_valuation_daily`, `monitor_signal_daily` and their twins (approved); quota read after
- [x] 5.4 P4: the dev dashboard opens for the user, every widget shows data; descriptions visible in UC

## 6. After merge

- [ ] 6.1 prd: CI runs `investments`; P1 old vs new equal in prd; prd = dev for the latest day
- [ ] 6.2 Drop prd `index_valuation_daily`, `monitor_signal_daily` and their twins (approved); quota read after
- [ ] 6.3 prd dashboard opens for the user
- [ ] 6.4 Planning: story design change list (Genie agent is change 5)
