## Context

- `strategy_states_query` (`strategy_events_sql.py`) gives, per strategy 002 member and complete week: the close, the week
  change, `down_week_count` (the current streak of weekly closes down, 0 in a week up), `price_to_sales_ratio`, `is_red`
  and `is_setup_on`. The dashboard already reads it (`STATES` in `strategy_queries.py`).
- `ds_short_candidates` lists only states with `is_setup_on` in the as-of week (`SHORT_WEEK`), so a stock leaves the table
  the week one check fails.
- Probe P18 (prd): NVDA, climate red every day; weeks down 3, 4, 5, 6, 7 on 2026-10-23 to 2026-11-20; price-to-sales
  16.78, 16.28, 14.85, 12.95, 9.99; setup on 2026-10-23 and 2026-10-30 only; no entry.

## Goals / Non-Goals

**Goals:** show every started setup with each rule of strategy 002 as a light, including the rule that fails.

**Non-Goals:** changing the rules; changing the candidates or events tables; history of the checks over time.

## Decisions

### D1. Which stocks are listed

A streak is identified by its first week down: `date_sub(week_start, 7 * down_week_count)` is the same for every week of
one streak. A stock is listed in the as-of week W when either

- W is a week down and some week of the same streak had `is_setup_on`, or
- W is a week up (`down_week_count = 0`) and the streak that ended the week before had a week with `is_setup_on`.

So a stock stays from its setup start until the week after its streak breaks (user, 2026-11-23). It stays while only
price-to-sales or the climate fails, as long as it keeps falling. "Setup met on" is the first week of the streak with the
setup on.

### D2. Lights

A light answers "does this rule pass?", so a red climate gives a green climate check. A note above the table says so.

| Check | Green | Yellow | Red | Grey |
|---|---|---|---|---|
| Climate | a light is red | | no light red | |
| Weeks down | 6 (entry week) | 3 to 5 | 0 (rose this week) | above 6 (entry week passed) |
| Price-to-sales | above 15 | | 15 or below, or no value | |
| Entry | an entry fired in this streak | | | none yet |

Weeks down is shown as `n/6`, and as `n (entry week passed)` above 6. Thresholds come from `strategy.py`
(`SETUP_DOWN_WEEKS`, `DOWN_WEEKS_FOR_ENTRY`, `PRICE_TO_SALES_MIN`).

### D3. Page layout

The new table goes between the candidates and the latest events, full width, ordered by weeks down then symbol. The
dashboard's date drives it like the other Short Selling datasets (`DATE_DATASETS`).

### D4. Genie

`EXAMPLES` gets the new dataset: "Which short setups started and which rule fails?". The benchmarks stay; the evaluation
runs on dev before merge and on prd after.

## Risks / Trade-offs

- A missing week of prices would split a streak in two (the streak id moves). Weeks are complete Monday-based weeks of
  `^GSPC`, so this needs a stock with no price for a whole week; accepted.
