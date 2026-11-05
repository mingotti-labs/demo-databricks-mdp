## Why

Change 4 of 5 of the market climate story (planning `docs/superpowers/specs/2026-11-04-market-climate-story-design.md`;
rules, definitions and the worked example in `references/user-stories/monitor-understand-market-climate.md`).
Gold holds two lights per day, but only as index totals: a person cannot see which companies make the
P/E what it is, so the light cannot be checked, and once trusted, cannot be explained. This change keeps
every member's figures per day in gold, so each light traces back to rows (light -> answers -> index totals
-> member rows -> silver filing and price), and puts the climate and its drilldown on a dashboard.
The Genie agent follows in change 5 and reuses the dashboard's tested queries.

## What Changes

- **New `valuation_daily_index_member`**: one row per index, current member and day. The per-member
  step that sits inside the gold query today (main listing, price at most 5 days old, the filing valid
  that day, the share count and its source, 10-year earnings in that day's money), plus whether the member
  is used and, if not, why; its share of the index market value; the index P/E without it and its effect
  on the index P/E.
- **`index_valuation_daily` renamed `valuation_daily_index`**, now the sum of the member rows per day.
  Same columns, same values (checked day by day against the old table before it is dropped).
- **`monitor_signal_daily` renamed `monitor_daily_signal`**, same rows (checked the same way).
- **Naming rule** for gold tables (user, 2026-11-05): subject first, then grain, then detail, so related
  tables sort together. NAMING.md says so.
- **Dashboard "Market Climate"** (`resources/dashboards/`), on the gold tables, four pages (*Company Deep Dive*, added in implementation: price chart with Bollinger bands and the steps behind one company's P/E):
  - *Climate*: "Climate as of" date and the freshness of each input; both lights with their three
    answers and reasons; the history of both lights; three drilldown charts (P/E with the lens lines, Fed
    target with hikes and cuts, S&P 500 with its 200-day average).
  - *Climate Deep Dive*: for a chosen day, the members that push the P/E up most and down most, the
    members left out and why, all members (filter by sector, used or not), and the checks (member rows
    add up to the index row; one company worked through).
  - *Sector Deep Dive*: a sector selector; the sector's P/E against the index P/E, the index P/E without
    the sector, and the sector's members that push it up and down most.
- **Sector** comes from `silver_domain_investments.company` by `company_id` at query time; no copy in gold.
- **Old tables dropped** in dev and prd once the new ones match (user approved, 2026-11-05).
- **Verification** `verify_gold_market_climate.py` on the new names, plus: member rows add up to the index
  row, a row for every current member and day, and the "without" figures recompute.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `gold-market-climate`: member valuation per day; both tables renamed; the dashboard.

## Impact

- Table slots: +2 per environment for the member table, and +2 per environment while the renamed tables
  and the old ones both exist. Now 480 (quota API, 2026-11-05): dev peak 486, then 482 after the drop; prd
  peak 488, then 484. No new pipeline or schema.
- Anything reading the old names: the signals query, the verification notebook, probes, docs. No dashboard
  or Genie agent read them yet.
- Runs: gold code changes run `investments` (silver then gold) as before.
- Not in this change: the Genie agent (change 5); a sector aggregate table (only if change 5 or a later
  story needs it).

## Cross-repo dependencies

None. The CI/CD principal already writes `gold_analytics_gateway` (iac `gold-analytics-gateway-grants`), and
the `users` group can use the Serverless Starter Warehouse the dashboard runs on.
Planning repo: the story design's change list becomes five changes (Genie agent is change 5).

## Model

Sonnet: the tables, pages and checks are settled here; the dashboard JSON follows the
`databricks-aibi-dashboards` skill.
