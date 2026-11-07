## Why

The user changed story 002 (short selling) on 2026-11-07: the setup also needs the stock to be going down for three straight
weeks (planning `references/user-stories/strategy-002-short selling.md`); the entry stays at six straight weeks. Today's
setup is only a red climate light and price-to-sales above 15, so it turns on for a stock that is rising (TSLA on
2026-10-30, up 7.4% on the week). With the streak in the setup, it becomes the early warning the strategy needs: a stock
that is expensive, falling for three weeks and in a red market, three weeks before the entry can fire.

## What Changes

- Strategy 002's setup is on when a climate light is red, `price_to_sales_ratio` is above 15 and the stock's weekly adjusted
  close has been below the previous week's for at least 3 weeks in a row (`down_week_count` of 3 or more). One constant,
  `SETUP_DOWN_WEEKS = 3`, in `src/common/strategy.py`.
- A rising week ends the setup (the streak is back to zero). An entry still fires the week the streak reaches six while the
  setup is on, so it needs the setup unbroken from week three to week six.
- The `setup_start` row of a stock carries `down_week_count` 3 or more; reason texts, column descriptions, the gold
  verification and tests follow. Strategy 001 is unchanged.
- The number of weeks (3) was chosen with the user on 2026-11-07 from a comparison on prd (probe P11): 3, 4 and 5 weeks all
  keep both existing entries (LRCX, HOOD); setup starts a year: 47 (3 weeks), 17 (4), 8 (5), against 108 now; warning before the
  entry 3, 2 and 1 weeks.

## Capabilities

### New Capabilities

None.

### Modified Capabilities
- `gold-strategies`: the strategy 002 setup.

## Impact

- Table slots: none. Quota 488 of 500 (stop line 488).
- Runs: `investments` (the gold task) in prd after merge. The table is recomputed: strategy 002 goes from 108 setup starts,
  94 ends and 2 entries to about 47, 45 and 2 (prd, 2026-11-06); the two open setups are AMD and TPL.
- Not in this change: the dashboard (change 3), exits, positions.

## Cross-repo dependencies

None. Planning: story 002 (the setup rule) and the design's rules section are updated in the same session.

## Model

Sonnet for implementation: one condition, one constant, texts and a check on an existing view; the rule and the number are decided.
