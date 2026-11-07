## Context

- Dashboards are generated (`cicd/build_dashboards.py`): queries in `src/common/*_queries.py` (`dataset(name, title, sql)`),
  pages in `src/common/*_dashboard.py` with the shared widgets of `src/common/dashboard_widgets.py` (tables, filters,
  counters, Vega-Lite charts, the date and string parameters, the history range layer of `market-climate-range-filter`); a
  pytest checks the committed files equal the builders. Datasets read the target catalog and `gold_analytics_gateway`.
- The Genie agent `resources/genie/market_climate.genie.yml` is built by `src/common/market_climate_genie.py`: `GOLD_TABLES`,
  instructions (`market_climate_genie_instructions.md`), example SQL = the dashboards' queries with literal parameters,
  benchmarks.
- `strategy_daily_event` has a row only when something happens; the setup status of a week with no event is the latest
  event before it (on after a start or entry, off after an end).
- Mockups from the brainstorm (2026-11-06, visual companion, planning `.superpowers/`): the two tabs as below.

## Goals / Non-Goals

**Goals:** a page per strategy showing the setup and entry of the as-of week; past setup periods; a bear fund chart; the agent
answers about strategies.

**Non-Goals:** positions and sizing; exits as events; the current incomplete week (the as-of week is the latest complete
week); a backtest of returns.

## Decisions

### D1. One definition of the weekly states

`strategy_events_sql.py` gets `strategy_states_query(...)`: the weekly states of both strategies (today's `states` step:
strategy, symbol, week, closes, change, price-to-sales, weeks down, is the setup on), and `strategy_events_query` reads it.
The Bear Market Fund page shows the as-of week's state from it (the checks with their values), so a week with no event still
shows GO / NO GO and the numbers. Rejected: recomputing the checks in a dashboard query (two definitions that can drift);
a states table (2 more slots at the stop line).

### D2. The as-of week

A date parameter `as_of_date` (default today, as the other dashboards); the page shows the latest complete week whose last
day is on or before it. The exit checks use the same week (week change, close against five weeks earlier) and the VIX close of
its last day.

### D3. Candidates and past periods

Short Selling candidates: per symbol, the latest event on or before the as-of week; a candidate when it is a `setup_start`
or an `entry` (the period is open). Setup light green for every candidate; entry light green when the period has an
entry, else grey. Past signals (Bear Market Fund): a dropdown of `setup_start_date` values with the period's end date and
entry count in the label, and the events of the chosen period.

### D4. Bear Fund Deep Dive

A fund selector and the history range filter (36M default); two charts on one time axis (the fund close; the S&P 500
weekly close), setup periods as shaded rects (start to end, or to the as-of week when open), entries as points with
their band. The invisible range layer keeps the axes aligned.

### D5. Genie

`strategy_daily_event` joins `GOLD_TABLES`; the instructions add the two strategies' rules and how to read a period
(setup_start_date groups it; no setup_end yet means open); examples: the dashboard queries; benchmarks: "Is the bear market
fund setup on?", "When did the bear fund setup last start?", "Which stocks are short selling candidates this week?",
"Which entries fired in the last 6 months?". The evaluation runs in dev before merge.

## Risks / Trade-offs

- [The events query changes shape (states split out)] → the table output must stay identical: the probe compares the
  table before and after on dev.
- [The as-of week is up to a week old] → stated on the page next to the date.

## Migration Plan

Merge; CI deploys the dashboard and the agent in prd; the user checks the prd pages and agent. Rollback: revert.

## Open Questions

None.
