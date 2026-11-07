## Context

- `strategy_daily_event` (`strategy-events`, archived) builds strategy 002's weekly states in `src/common/strategy_events_sql.py`:
  `short_states` has `is_setup_on` = climate red and `price_to_sales_ratio` above 15, and `down_week_count` (the streak of
  weekly adjusted closes below the previous week's) is already computed for the entry.
- Probe P11 (`references/poc/strategies/p11_result_prd.txt`, prd tables, read only) ran the same query with the streak added to
  the setup for 3, 4 and 5 weeks.

## Goals / Non-Goals

**Goals:** the setup of story 002 as the user wrote it; the entry unchanged.

**Non-Goals:** a statistical test of how long a fall continues (the table has one year, from 2025-10-29; prices go back
decades, a possible later probe on prices alone), exits, positions, strategy 001.

## Decisions

### D1. The streak is part of the setup condition

`is_setup_on` for strategy 002 gains `down_week_count >= SETUP_DOWN_WEEKS`. Nothing else in the event logic changes: a
`setup_start` is the first week all conditions hold (the streak reaches 3), `setup_end` the first week one fails (a rising
week, price-to-sales at or below 15, no red light), entries fire while on at a streak of exactly 6. The stock must therefore
stay above 15 price-to-sales and keep falling from week 3 to week 6 to get an entry, so a stock whose price-to-sales falls
below 15 during the decline leaves the screen before its entry (TSLA, 2026-11-06). That follows from the user's rule
(price-to-sales "still over 15" in the setup) and is shown, not changed.

### D2. Three weeks

Probe P11, prd, one year of weekly states: 3 weeks gives 47 setup starts over 23 symbols, 4 gives 17 over 13 and 5 gives 8
over 7 (108 over 42 as built); all three keep the two entries (LRCX 2026-07-31, HOOD 2026-10-30) and the setups open on
2026-11-06 are AMD and TPL (3 or 4 weeks) or AMD (5). The setup is the early warning before the entry, so the lead time
matters: 3 weeks before the entry at 3, 2 at 4, 1 at 5. User choice 2026-11-07: 3. The constant makes another number a
one-line change.

### D3. Row contents

`down_week_count` is already on every strategy 002 row; a `setup_start` row now has 3 or more. Reason texts say which
conditions hold (start) or which failed (end: a rising week, price-to-sales at or below 15, or no red light). The gold
verification gains: a short selling `setup_start` has `down_week_count` of at least 3 and price-to-sales above 15.

## Risks / Trade-offs

- [Fewer setup rows (108 to 47) and a shorter candidate list] → intended; the monitor shows the list that matters.
- [A stock that rose one week during a long decline ends its setup and needs three new weeks] → follows from "three straight weeks".

## Migration Plan

Merge after the archive PR; CI runs `investments` in prd (the materialized view is recomputed; no data to migrate). Compare
prd with dev. Rollback: revert the PR.

## Open Questions

None.
