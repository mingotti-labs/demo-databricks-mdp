## Why

Change 2 of 3 for strategies 001 (bear market mutual fund) and 002 (short selling), design in planning
`docs/superpowers/specs/2026-11-06-strategies-001-002-design.md`. The user wants to see, every Friday, whether each
strategy's setup is on and whether its entry rule fired, and when that happened before. The rules need a place that
keeps the history: a gold table of strategy events, a row only when something happens (user, 2026-11-06).

## What Changes

- **New gold table `gold_analytics_gateway.strategy_daily_event`** (materialized view in the gold pipeline, file
  `src/layers/gold/analytics_gateway/strategy_daily_event.py`): one row per `strategy_code`, `trading_symbol_code`,
  `event_date` and `event_code` (`setup_start`, `entry`, `setup_end`); `strategy_name`, `event_name`, `listing_id`,
  `setup_start_date` (ties a setup period together), `entry_number` and `is_first_entry`, `entry_band_code` (001), the
  measured values, `reason_text`, `currency_code`, `ingested_timestamp`; every column described for a Genie agent.
- **Strategy 001 `bear_market_fund`** on `^GSPC`, every complete Monday-based week: setup = any market climate light red
  and the week close below the close five weeks earlier; entry = the week's change at most -5% (`half_of_equity`) or
  -2.5% (`quarter_of_equity`), or the interim entry (a Monday-Wednesday close at least 2.5% below the week just ended,
  after a week down less than 2.5%: `interim_quarter_of_equity`).
- **Strategy 002 `short_selling`** on the current S&P 500 members of each week's last day: setup = any light red and
  `price_to_sales_ratio` above 15 (from `strategy-inputs`); entry = the week the stock's streak of weekly closes down
  (adjusted) reaches six.
- Rules and thresholds in `src/common/strategy.py`, the query text in `src/common/strategy_events_sql.py` (probes run the
  same text); gold verification for the table.

## Capabilities

### New Capabilities
- `gold-strategies`: the strategy events table and its two strategies' rules.

### Modified Capabilities

None.

## Impact

- Table slots: +4 (a materialized view and its hidden twin, dev and prd): 484 to 488, the stop line. A table clean-up
  comes before the next story that adds a table. Read the quota before the dev run.
- Depends on `strategy-inputs` (price-to-sales, merged and run in prd first).
- History starts 2025-10-29 (the climate lights). Probe P1: 14 setup weeks for 001 and no entry so far; P3: six-week
  streaks are common (150 in a year), the price-to-sales filter keeps few.
- Runs: `investments` (the gold task) in prd.
- Not in this change: the dashboard and the Genie agent (change 3, after this table exists in prd), exits as events,
  positions.

## Cross-repo dependencies

None (schema `gold_analytics_gateway` and its grants exist).

## Model

Sonnet for implementation: a gold materialized view, rules module and verification, like `monitor_daily_signal`; the
rules are fully stated in the design and the specs.
