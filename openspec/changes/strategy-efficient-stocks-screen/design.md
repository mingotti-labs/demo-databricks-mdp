## Context

- `price_indicator_daily` (silver) has per listing and day `efficiency_r60_ratio`, `efficiency_tr60_ratio`,
  `close_sixty_day_change_ratio`, `price_range_sixty_day_average_ratio`, `true_range_sixty_day_average_ratio` and
  `volume_sixty_day_average_count`.
- `valuation_daily_index_member` (gold) has every current S&P 500 member per day with the `listing_id` whose price is used
  (the company's most traded listing); strategy 002 takes its members from it.
- The Strategy Monitor is generated (`strategy_queries.py`, `strategy_dashboard.py`); its date filter drives every dataset
  in `DATE_DATASETS`. Genie examples come from `EXAMPLES` in `market_climate_genie.py`, benchmarks from `BENCHMARKS` and
  `extra_benchmarks()`.
- Probe E3 and the table of 2026-11-06 (dev): no member passes; PTC 13.3, MRNA 11.4 (one jump of 176%), ACN 10.7.

## Goals / Non-Goals

**Goals:** strategy 004's screen on the Strategy Monitor and in the agent, with the closest stocks shown while none pass.

**Non-Goals:** numbers for the smoothness rules (the story gives none), setup, entry and exit, rows in
`strategy_daily_event`, history of the screen over time, a table.

## Decisions

### D1. Screen rules

`EFFICIENT_STOCKS_CODE = "efficient_stocks"`, `EFFICIENCY_MIN = 15` and `EFFICIENT_VOLUME_MIN = 200_000` in
`strategy.py`. A stock passes when r60 >= 15, tr60 >= 15 and the 60-day average volume > 200,000 (my call: both ratios,
since the story names one "efficiency number" and the user defined two; a stock with r60 >= 15 and tr60 < 15 is shown with
a yellow efficiency light and does not pass). A function `efficient_stock_passes(r60, tr60, volume)` is the reference for
the tests.

The smoothness rules of the story (a smooth 60-day rise, no flat-jump-flat pattern, not parabolic, no sudden widening of
the daily range) are listed on the page as "not checked yet" until the user gives them numbers.

### D2. Day and members

The day is the latest `^GSPC` price date on or before the dashboard's date. The members are the rows of
`valuation_daily_index_member` on that day (as strategy 002), joined to `price_indicator_daily` on `listing_id` and the
day. A member without indicators that day (too little history) is left out.

### D3. Page "Efficient Stocks"

After "Short Selling": a text with the rules (the story's screen and that the smoothness rules are not checked yet), a
summary table (day, members screened, members passing, the text "No stock passes today" or the count), and the table of the
20 members with the highest r60 that day: symbol, company, r60, tr60, 60-day change, average range and true range as a share
of the close, average volume, and lights (efficiency: green both >= 15, yellow one, grey none; volume: green or grey;
passes: green or grey). Datasets `ds_efficient_summary` and `ds_efficient_closest`, both date-bound.

### D4. Genie

Instructions: the screen rules and that a stock passes on both ratios and the volume. Examples: the two datasets. One
benchmark: "Which stocks are closest to passing the efficient stocks screen?" answered by `ds_efficient_closest` with the
latest day (not "which pass", which is empty today and would not test the agent).

## Risks / Trade-offs

- [Both ratios required is my call] → the lights show each; changing to r60 only is one line.
- [No history of the screen] → the date at the top shows any past day; a history comes with entries and events.

## Migration Plan

Merge; CI deploys the dashboard and the agent; no unit runs. Rollback: revert.

## Open Questions

None.
