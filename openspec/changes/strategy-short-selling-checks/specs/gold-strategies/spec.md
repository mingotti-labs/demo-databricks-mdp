## MODIFIED Requirements

### Requirement: Strategy Monitor dashboard
A dashboard "Strategy Monitor" SHALL read the target's catalog and show, as of the latest complete week on or before a date
that defaults to today: on page "Bear Market Fund", strategy 001's setup checks with their values and GO or NO GO, the
week's change with the entry band and the action, the exit checks (week up 3% or more, close above five weeks earlier, VIX
above 50), the five bear funds with last close and week change, and the events of a past setup period chosen from a list;
on page "Bear Fund Deep Dive", a chosen bear fund's close and the S&P 500 over a chosen history range with the setup
periods shaded and the entries marked; on page "Short Selling", the climate gate, the candidates (open setup periods)
with symbol, company, setup start date, price-to-sales, weeks down, a setup light and an entry light, and the rule checks
of every started setup: one row per stock whose setup was on at least once in its current streak of weekly closes down,
kept until the week after the streak breaks, with the climate, weeks down (n/6) and price-to-sales each with a light that
says whether the rule passes, the setup start date and an entry light. The setup status SHALL come from the same weekly
states as `strategy_daily_event`.

#### Scenario: A week with no event
- **WHEN** the as-of week has no strategy 001 event and the setup started two weeks earlier
- **THEN** the page shows GO with the week's checks and values

#### Scenario: An open short setup
- **WHEN** a stock's latest event on or before the as-of week is a `setup_start`
- **THEN** it is listed as a candidate with a green setup light and a grey entry light

#### Scenario: A setup that lost price-to-sales
- **WHEN** the as-of week is the week to 2026-11-13 in prd and NVDA's setup started on 2026-10-23
- **THEN** NVDA is listed in the rule checks with climate red and a green check, 6/6 weeks down with a green check,
  price-to-sales 12.95 with a red check and a grey entry light, and it is not a candidate

#### Scenario: Weeks down still short of six
- **WHEN** a stock's setup is on with four weeks down
- **THEN** it is listed in the rule checks with 4/6 weeks down and a yellow check

#### Scenario: The streak breaks
- **WHEN** a listed stock closes a week up
- **THEN** that week it is listed with 0/6 weeks down and a red check, and the next week it is not listed
