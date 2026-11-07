## Why

Change 3 of 3 for strategies 001 (bear market mutual fund) and 002 (short selling); design in planning
`docs/superpowers/specs/2026-11-06-strategies-001-002-design.md` ("What the user sees"). The events table
`gold_analytics_gateway.strategy_daily_event` is in dev and prd (`strategy-events`, `strategy-short-selling-setup`). The
user wants to open a dashboard on a Friday evening and see, per strategy, whether the setup is a go, whether the entry
fired, and when it happened before; and to ask the Genie agent the same.

## What Changes

- **Dashboard "Strategy Monitor"** (generated like the other three: `src/common/strategy_queries.py`,
  `src/common/strategy_dashboard.py`, `src/dashboards/strategy_monitor.lvdash.json`,
  `resources/dashboards/strategy_monitor.dashboard.yml`, an entry in `cicd/build_dashboards.py`):
  - page **Bear Market Fund**: an as-of date (the latest complete week on or before it); the setup checks (a red climate
    light; the S&P 500 week close against five weeks earlier) with GO / NO GO; the week's change and the entry band with
    the action ("invest a quarter of equity in the bear fund on Monday"); the exit checks as live yes/no (week up 3% or more,
    close above five weeks earlier, VIX above 50); the five bear funds with last close and week change; past signals: a
    setup period dropdown and that period's events; the allocation rules as text.
  - page **Bear Fund Deep Dive**: a fund selector (SQQQ, PSQ, SH, SDS, SPXU) and the history range of the Market Climate page;
    the fund's close and the S&P 500 on one time axis, the setup periods shaded and the entries marked.
  - page **Short Selling**: the climate gate (red: strategy allowed); the candidates of the as-of week (open setup periods):
    symbol, company, setup start date, price-to-sales, weeks down, setup light, entry light; the latest events; the rules and
    precautions as text (3 to 5 stocks, 1% risk each; exits need a position).
- **Weekly states shared with the table**: `src/common/strategy_events_sql.py` exposes the weekly states (setup on or off,
  the measures) as their own query, used by the events query and by the dashboard, so both read one definition.
- **Genie agent "Investment Intelligence"**: `strategy_daily_event` in its tables, the two strategies' rules in its
  instructions, examples from the dashboard queries and four benchmarks.

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `gold-strategies`: the Strategy Monitor dashboard and the strategies' part of the Genie agent.

## Impact

- Table slots: none (a dashboard and agent changes). Quota 488 of 500.
- The table exists in prd, so the agent update does not deadlock the deploy (mdp CLAUDE.md operational note).
- Runs: none needed for data; the deploy publishes the dashboard and updates the agent.
- Not in this change: positions, exits as events, a backtest of returns, strategies 003-006.

## Cross-repo dependencies

None. Planning: the design's status after the change.

## Model

Sonnet for implementation: a fourth generated dashboard and agent additions on the existing builders; the pages are agreed.
