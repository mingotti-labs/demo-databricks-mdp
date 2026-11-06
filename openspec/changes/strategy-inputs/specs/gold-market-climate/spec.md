## ADDED Requirements

### Requirement: Price-to-sales per member and day
`gold_analytics_gateway.valuation_daily_index_member` SHALL carry `revenue_trailing_twelve_months_amount` (the `revenue`
of the member's valid filing row) and `price_to_sales_ratio` (`market_value_amount` divided by that revenue), empty when
either is missing or the revenue is not above zero, each with a Unity Catalog description. A missing revenue SHALL NOT
change `is_used`, `exclusion_reason_code` or any price/earnings column.

#### Scenario: A member with revenue
- **WHEN** a member's market value on a day is 300 bn and its valid filing's trailing revenue is 20 bn
- **THEN** its row for that day has `price_to_sales_ratio` 15

#### Scenario: A member without revenue
- **WHEN** a used member's valid filing has no revenue
- **THEN** its `price_to_sales_ratio` is empty and it stays used in the index P/E
