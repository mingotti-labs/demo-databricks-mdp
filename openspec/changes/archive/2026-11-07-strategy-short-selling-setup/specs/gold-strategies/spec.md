## MODIFIED Requirements

### Requirement: Strategy 002 short selling
For `strategy_code` `short_selling`, on each current S&P 500 member of a week's last day, the setup SHALL be on when the
climate is red, the member's `price_to_sales_ratio` that day is above 15 and its weekly adjusted close has been below the
previous week's for at least 3 weeks in a row. While the setup is on, an `entry` SHALL be written on the week its streak of
weekly adjusted closes below the previous week's reaches six. A member absent from the index on a week's last day SHALL
count as setup off. Rows SHALL carry `price_to_sales_ratio` and `down_week_count` (3 or more on a `setup_start`).

#### Scenario: Three weeks down starts the setup
- **WHEN** the climate is red, a member's price-to-sales is above 15 and its weekly close has fallen three weeks in a row
- **THEN** a `setup_start` is dated on the third week's last day with `down_week_count` 3

#### Scenario: A rising stock has no setup
- **WHEN** the climate is red, a member's price-to-sales is above 15 and its weekly close rose this week
- **THEN** it has no setup that week, and a setup it had ends with a `setup_end`

#### Scenario: Six weeks down
- **WHEN** a member's setup is on and its adjusted weekly close has fallen six weeks in a row
- **THEN** an `entry` is dated on the sixth week's last day, and a seventh week down writes no new entry

#### Scenario: No revenue
- **WHEN** a member's `price_to_sales_ratio` is empty
- **THEN** its setup is off
