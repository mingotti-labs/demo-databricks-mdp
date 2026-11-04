## Context

Inputs (all `silver_domain_investments`): `index_membership` (current S&P 500 members), `listing`,
`price_daily`, `company_fundamentals` (point in time by `valid_from_date`/`valid_to_date`; cover and
weighted average share counts; `net_income` trailing 12 months; the rolling 10-year averages in
period-end money with `consumer_price_index_value`), `price_indicator_daily` (`^GSPC` 200-day average and
slope), `market_rate_daily` (`us_federal_funds_target_upper`, `us_cpi_all_items_not_seasonally_adjusted`).
Story probe P1 found the index P/E (10-year, inflation-adjusted) 40.8 and trailing 24.7 on 2026-11-02
with 458 members; changes 1-2 raised share coverage to 492 of 500.

## Goals / Non-Goals

**Goals:** every figure behind a light traceable to rows and thresholds; one long signals table for every
monitor; gold always after silver.

**Non-Goals:** index membership history (today's members for every date, as the story says); prices
before 2025-10-28 for members; the dashboard and Genie agent (change 4).

## Decisions

### D1. Who counts on a day
Members = current index members, one listing per company: the listing with the highest average volume
over its last 60 price rows (GOOGL for Alphabet). On day D a member is *used* when it has a close on or
within 5 days before D, a `company_fundamentals` row valid on D with a share count (cover, else weighted
average), `net_income`, and both 10-year averages. Every total and every ratio of the day uses the same
used members, so the three P/Es are comparable. Coverage columns: `member_count`, `members_used_count`,
`members_without_shares_count`, `members_under_ten_years_count` (used members with `earnings_year_count` < 10).

### D2. Today's money
`consumer_price_index_value` of a day = US CPI of the latest month on or before D with a value (same rule
as silver). A member's inflation-adjusted average in today's money = its stored average x (CPI of D /
its row's `consumer_price_index_value`).

### D3. `index_valuation_daily` columns
`index_code`, `valuation_date`, `market_value_amount`, `earnings_trailing_twelve_months_amount`,
`earnings_ten_year_average_amount`, `earnings_ten_year_average_inflation_adjusted_amount`,
`price_earnings_trailing_twelve_months_ratio`, `price_earnings_ten_year_average_ratio`,
`price_earnings_ten_year_average_inflation_adjusted_ratio`, `consumer_price_index_value`, the four counts
(D1), `currency_code` (`USD`), `ingested_timestamp` (earliest input). Days: the `^GSPC` price dates from
the first date any member has a price.

### D4. `monitor_signal_daily` columns and rules
`signal_date`, `monitor_code`, `monitor_name`, `lens_code`, `lens_name`, `signal_code`, `signal_name`,
`is_yes` (answer rows; empty on result rows), `band_code` (`green`/`yellow`/`red`; on a result row the
light), `measured_value`, `threshold_value`, `reason_text` (one plain sentence), `yes_count` and
`action_name` (result rows only), `ingested_timestamp`. Key: (`signal_date`, `monitor_code`, `lens_code`,
`signal_code`).
- `too_expensive`: measured = P/E (10-year, inflation-adjusted); yes when above the lens line (22 long
  run, 30 modern); band green below 16 / 22, yellow up to 22 / 30, red above.
- `fed_in_the_way`: change days of `us_federal_funds_target_upper` (value differs from the previous
  day's); yes when the latest change on or before D was a hike and D is before that day plus 6 months;
  band red when yes, green when the latest change was a cut less than 6 months ago, yellow otherwise;
  measured = the target, threshold = the target before the latest change. Same rows in both lenses.
- `market_going_up`: `^GSPC` close vs its 200-day average (threshold); yes when the close is above it
  (the unfavourable answer: the strategies find signals below the average); band green above with slope
  >= 0.002, yellow above with a smaller or negative slope, red at or below. Same rows in both lenses.
- `climate`: yes count of the lens's three answers; red 2-3 (sell), yellow 1 (buy and hold), green 0
  (strong buy). Only on days with all three answers.

### D5. Run order inside one unit
`run_investments`: `silver` -> `verify_silver_domain` (when verify) -> `gold` (`run_if: NONE_FAILED`, so it
runs when verification is off and not after a failed check) -> `verify_gold` (when verify) -> `tag_patterns`.
Rejected: a separate `run_market_climate` unit with a `run_job_task` on `run_investments` (the pattern
`affected_units.py` suggests): every gold run would rebuild silver, and an investments change would run both.

### D6. Thresholds in code
`src/common/market_climate.py` holds the lines, bands, window and flat slope as constants, with SQL
helpers and tests; the story calls them hard-coded. Moving them to the `portfolio` settings CSV would
version them; not needed yet.

### D7. Descriptions
Both tables declare their full schema with a `COMMENT` per column (silver probe P1: a view must list every
column to describe any). Descriptions say the formula, units, which lens, and that the 10-year windows roll.

## Risks / Trade-offs

- [Eight members have no share count (ARES, BRK.B, ERIE, HSY, STZ, TSN, V, VYLR); BRK.B and V are large]
  -> they are left out of every total that day and counted in `members_without_shares_count`; the P/E is of
  the members used. A later change can add per-class shares.
- [Today's members for past days] -> stated in the story and in the table descriptions.
- [The first 200 trading days of member prices give no history depth for the trend] -> the trend uses
  `^GSPC` (from 1970), not members.

## Migration Plan

iac #79 applied -> merge -> CI runs `investments` (silver, then gold) in prd. No by-hand runs needed.
Rollback: revert; drop the two gold tables, their twins and the event log with approval.

## Open Questions

None.
