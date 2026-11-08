## Why

Strategy 004 (Trading Efficient Stocks) has its indicators in `price_indicator_daily` since
`us-yields-and-efficiency-indicators`: the efficiency ratios r60 and tr60 and the 60-day average volume. The user wants the
strategy on the Strategy Monitor now, even though no stock passes the screen today (2026-11-06: highest tr60 10.3, MRNA),
and then to move on to strategy 005. The story has screening rules only; its setup, entry, exit and the numbers of its
smoothness rules are not written yet.

## What Changes

- Strategy Monitor, new page "Efficient Stocks": the screen of the day (latest trading day on or before the dashboard's
  date) over the S&P 500 members, with the rules, how many stocks pass, and the 20 members closest to passing (highest
  tr60) with tr60, r60 (for information), the 60-day change, the average range and true range as a share of the close, the average volume and
  a light per rule. The story's smoothness rules are listed as not checked yet.
- Screen rules as constants in `src/common/strategy.py`: tr60 15 or more, 60-day average volume above 200,000 shares.
  r60 is shown for information only and does not decide.
- Genie agent: the screen in its instructions, the page's queries as examples and one benchmark ("Which stocks are closest
  to passing the efficient stocks screen?").
- No rows in `strategy_daily_event`: a screen is not a setup or an entry; events come with the entry rules.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `gold-strategies`: strategy 004's screen on the Strategy Monitor and in the Genie agent.

## Impact

- Table slots: none (dashboard queries over existing tables). Quota 488 of 500 by the table inventory; the quota API's
  last reading said 496 (to be read again before any change that adds a table).
- Dashboards: Strategy Monitor (one page), the Genie agent file (examples, one benchmark, instructions).
- Not in this change: smoothness rules with numbers, setup, entry, exit, events for strategy 004; strategy 005.

## Cross-repo dependencies

None.

## Model

Sonnet: one page and two datasets on the Strategy Monitor's established pattern, plus Genie examples.
