## Context

- Gold pipeline `gold--analytics_gateway--<target>` builds every `.py` in `src/layers/gold/analytics_gateway/` (glob),
  run as the `gold` task of `run_investments` after silver. `monitor_daily_signal` holds the market climate rows
  (`monitor_code = 'market_climate'`, `signal_code = 'climate'`, lenses `long_run` and `modern`, `band_code` red /
  yellow / green), from 2025-10-29.
- Silver `price_daily` (`listing_id`, `trading_symbol_code`, `price_date`, `price_close`, `price_close_adjusted`);
  gold `valuation_daily_index_member` gives the current members per day and, after `strategy-inputs`,
  `price_to_sales_ratio`.
- Probes in `references/poc/strategies/` (P1 strategy 001 on prd, P3 six-week streaks on prd).

## Goals / Non-Goals

**Goals:** one events table for both strategies; setup periods with their entries; a row only when something happens.

**Non-Goals:** exits as events, positions or sizing, a backtest of returns, a weekly price table, the dashboard.

## Decisions

### D1. Weeks from daily prices

A week is Monday-based (`date_trunc('WEEK', price_date)`); its close is the close of its last trading day. A week is
complete when its last trading day is a Friday or its Friday has passed (`current_date()` after it), so a week that
ends on Thursday because Friday is a holiday is evaluated with Thursday's close; only complete weeks are evaluated, so the current
week writes nothing until it ends (the dashboard shows it as provisional). The S&P 500 uses `price_close`; stocks use
`price_close_adjusted` (a split must not look like a fall). Rejected: a weekly table (the user's daily-data rule; costs
slots).

### D2. Red light

"Red" = either climate lens `red` on the week's last day (user, 2026-11-06). A week whose last day has no climate row
(before 2025-10-29) is not evaluated.

### D3. Events from week states

Per strategy and symbol, each evaluated week is setup on or off. `setup_start` on the first week on (the previous
evaluated week off or none), `setup_end` on the first week off after an on week, both dated on the week's last day.
`setup_start_date` on every row is the date of the period's `setup_start`. Entries while the setup is on are numbered
by date within the period (`entry_number`, `is_first_entry` on number 1). A member absent from the index on a week's last
day counts as setup off.

### D4. Strategy 001 entries

On a setup week: change (close over the previous week's close, minus 1) at most -0.05 → `half_of_equity`; at most
-0.025 → `quarter_of_equity`; dated on the week's last day. Change below 0 and above -0.025 → the first Monday, Tuesday
or Wednesday of the next week whose close is at least 2.5% below this week's close → `interim_quarter_of_equity`, dated
on that day, in the same setup period. The 50% cap and the 25% steps are the user's to apply (dashboard text).

### D5. Strategy 002 entries

On a setup week of a member: the streak of consecutive weeks whose adjusted close is below the previous week's reaches
exactly six that week → an entry. A longer streak does not repeat it; a new streak reaching six in the same period is
the next entry.

### D6. One query, two strategies

The table is the union of one query per strategy over shared week and event steps (`src/common/strategy_events_sql.py`),
thresholds in `src/common/strategy.py` (unit-tested text, as `market_climate_signals_sql.py`). Probes run the same text
against prd before deploy.

## Risks / Trade-offs

- [Quota at the stop line] → read it before the dev run; stop if above 484 before the change.
- [Few or no 001 entries in the one-year history] → expected (P1); the table still shows setup periods.
- [Price-to-sales empty for a member] → that member never sets up for 002 (no false candidate).

## Migration Plan

Merge after `strategy-inputs` has run in prd; CI runs `investments`; compare prd with dev (event counts per strategy and
code). Rollback: revert; drop the table and its twin with approval to free the 4 slots.

## Open Questions

None.
