## Why

On 2026-11-13 NVDA closed its sixth straight week down with the market climate red, but strategy 002 gave no entry. Probe
P18 (`references/poc/strategies/p18_nvda_short_gate.py`, prd) showed why: its setup started on 2026-10-23 and ended on
2026-11-06, when its price-to-sales fell to 14.85 (12.95 on 2026-11-13). The rule worked as written, but the Short Selling
page could not show it: the candidates table lists only open setups, so a stock disappears the week a check fails. The
user wants one row per stock whose setup started, with each rule as a traffic light, to see at a glance which rule holds
and which fails.

## What Changes

- Short Selling page, new table "Setups started: rule checks", below the candidates: one row per stock whose setup was on
  at least once in its current streak of weeks down, kept until the week after the streak breaks. Columns: symbol,
  company, setup met on, climate and its check, weeks down (n/6) and its check, price-to-sales and its check, entry light.
- The candidates table ("Candidates: setups open this week") and the latest events table stay as they are.
- Genie agent: the new query as an example ("Which short setups started and which rule fails?").
- No rule change, no new table, no rows added to `strategy_daily_event`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `gold-strategies`: the Short Selling page shows the rule checks of every started setup.

## Impact

- Table slots: none (one dashboard query over the existing weekly states).
- Dashboards: Strategy Monitor (one table on the Short Selling page), the Genie agent file (one example).
- Not in this change: changing the price-to-sales rule (checked only at setup start, for example), which would need its
  own probe of how many more entries it gives.

## Cross-repo dependencies

None.

## Model

Sonnet: one dataset and one table on the Strategy Monitor's established pattern, plus a Genie example.
