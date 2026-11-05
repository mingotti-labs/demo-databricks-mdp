## ADDED Requirements

### Requirement: Market climate Genie agent
A Genie agent "Market Climate" SHALL be deployed with the bundle in every target, on the target's SQL
warehouse, over `gold_analytics_gateway.valuation_daily_index`, `valuation_daily_index_member` and
`monitor_daily_signal` and `silver_domain_investments.company` and `price_daily` of the target's catalog,
and the `users` group SHALL be able to ask it questions. Its instructions SHALL state the story's rules:
the three questions with their thresholds per climate (P/E 10-year inflation-adjusted above 22 for long run
and above 30 for modern; the latest change of the Fed target was a hike less than 6 months ago; the S&P 500
closes above its 200-day average), that yes is the unfavourable answer, the lights (2 or 3 yes red = sell,
1 yellow = buy and hold, 0 green = strong buy), the three P/E measures and that only the 10-year
inflation-adjusted one votes, the meaning of a member's effect on the index P/E (one at a time, not
additive), and the exclusion reasons. Its example SQL SHALL be the dashboard's queries for the same
questions, so the agent and the dashboard give the same figures. Its benchmark questions SHALL each carry
the SQL answer they are checked against.

#### Scenario: The light of the day
- **WHEN** a user asks the agent "what is the market climate today?"
- **THEN** it answers with both lights, their yes counts and the climate date, equal to the dashboard's
  "Market Climate as of" tile

#### Scenario: A company's P/E looks wrong
- **WHEN** a user asks why EQT's P/E is 749 while finance sites show about 12
- **THEN** the agent explains that 749 is the P/E on 10-year inflation-adjusted earnings and 12 the trailing
  P/E, with both figures from `valuation_daily_index_member`

#### Scenario: The same agent in every target
- **WHEN** the bundle deploys to dev and to prd
- **THEN** each agent reads only its own target's catalog
