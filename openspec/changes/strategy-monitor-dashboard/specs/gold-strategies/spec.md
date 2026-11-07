## ADDED Requirements

### Requirement: Strategy Monitor dashboard
A dashboard "Strategy Monitor" SHALL read the target's catalog and show, as of the latest complete week on or before a date
that defaults to today: on page "Bear Market Fund", strategy 001's setup checks with their values and GO or NO GO, the
week's change with the entry band and the action, the exit checks (week up 3% or more, close above five weeks earlier, VIX
above 50), the five bear funds with last close and week change, and the events of a past setup period chosen from a list;
on page "Bear Fund Deep Dive", a chosen bear fund's close and the S&P 500 over a chosen history range with the setup
periods shaded and the entries marked; on page "Short Selling", the climate gate and the candidates (open setup periods)
with symbol, company, setup start date, price-to-sales, weeks down, a setup light and an entry light. The setup status
SHALL come from the same weekly states as `strategy_daily_event`.

#### Scenario: A week with no event
- **WHEN** the as-of week has no strategy 001 event and the setup started two weeks earlier
- **THEN** the page shows GO with the week's checks and values

#### Scenario: An open short setup
- **WHEN** a stock's latest event on or before the as-of week is a `setup_start`
- **THEN** it is listed as a candidate with a green setup light and a grey entry light

### Requirement: Strategies in the Genie agent
The Genie agent "Investment Intelligence" SHALL list `strategy_daily_event`, carry both strategies' rules in its
instructions, have examples from the Strategy Monitor queries, and benchmarks that ask whether the bear fund setup is on,
when it last started, which stocks are short selling candidates and which entries fired recently. Its benchmark evaluation
SHALL pass in dev before merge.

#### Scenario: Candidates question
- **WHEN** a user asks the agent "Which stocks are short selling candidates this week?"
- **THEN** it answers with the open setup periods of the latest complete week, the same list as the Short Selling page
