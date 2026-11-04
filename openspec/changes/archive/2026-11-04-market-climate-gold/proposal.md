## Why

Change 3 of 4 of the market climate story (planning `docs/superpowers/specs/2026-11-04-market-climate-story-design.md`;
rules, definitions and the worked example in `references/user-stories/monitor-understand-market-climate.md`).
Silver now holds every input (changes 1-2): share counts for all classes, rolling 10-year earnings per
filing, CPI, the 200-day average and `^GSPC`. This change builds the first gold tables: the S&P 500's
valuation figures per day, and the two market climates (long run, modern) with their three yes/no
answers, in a table the next monitoring stories add rows to.

## What Changes

- **Gold pipeline** `gold_analytics_gateway` (display `gold--analytics_gateway--<target>`), serverless,
  reading `silver_domain_investments`, writing `gold_analytics_gateway`.
- **`index_valuation_daily`**: one row per index and day (`index_code` `SP500`) from the first day with
  member prices (2025-10-28): market value, the three earnings totals (trailing 12 months, plain 10-year
  average, inflation-adjusted 10-year average in today's money), the three P/E ratios, CPI today and
  coverage counts.
- **`monitor_signal_daily`**: one row per day, monitor, lens and signal. Market climate writes, per lens
  (`long_run`, `modern`), three answer rows (`too_expensive`, `fed_in_the_way`, `market_going_up`) and a
  result row (`climate`, named "Market climate long run" / "Market climate modern") with the yes count,
  the light and its action. Answer rows exist wherever their inputs do (Fed from 2008-12, trend from
  1970); result rows only where all three answers exist.
- **Thresholds** in `src/common/market_climate.py` with tests: valuation lines 22 (long run) and 30
  (modern), drilldown bands 16/22 and 22/30, Fed window 6 months, trend "flat" slope 0.002.
- **Run order**: `run_investments` gains `gold`, `verify_gold` after `silver`, so gold always runs after
  silver in one unit (CI runs units alphabetically and does not follow data dependencies).
- **Column descriptions** on every column of both tables (for the Genie agent, change 4).
- **Naming**: gold tables follow the Silver Domain rules (singular, grain suffix); new ending `_text` for
  a sentence (`reason_text`). NAMING.md and `silver.md` say so; the "TBD" goes.
- **Verification** `verify_gold_market_climate.py`: keys, coverage, rule consistency, an independent
  recomputation of one member's market value.

## Capabilities

### New Capabilities
- `gold-market-climate`: index valuation per day and the market climate signals.

### Modified Capabilities
- `silver-domain-investments`: `run_investments` also runs the gold pipeline and its verification.

## Impact

- Table slots: 2 materialized views plus the gold pipeline's event log, 5 per environment, 10 in all
  (about 470 to 480; stop line 488).
- Runs: any change to silver or gold code runs `investments` (silver then gold).
- Not in this change: the dashboard and the Genie agent (change 4).

## Cross-repo dependencies

Depends on `gold-analytics-gateway-grants` in `demo-databricks-iac` (PR #79): the CI/CD principal needs
write grants on `gold_analytics_gateway` before this change deploys to dev.

## Model

Sonnet: the rules and columns are settled here and in the story.
