## MODIFIED Requirements

### Requirement: Listings
`listing` SHALL have one row per `listing_id`: the SHA-256 hash of
`market_code` and `trading_symbol_code` joined by `:`. A listing is
one trading symbol on one market. It SHALL carry `market_code`,
`trading_symbol_code` (the Wikipedia form with dots, as in Landing),
`currency_code`, `company_id` (empty for an index benchmark) and the options
columns below. Listings SHALL
come from every symbol in the Wikipedia S&P 500 history and from the
`portfolio` benchmarks. The market of a symbol SHALL be the operating market identifier code
mapped from the `exchange_code` of the latest version of the symbol's Yahoo
calendar row (`NMS`, `NGM`, `NCM` to `XNAS`; `NYQ`, `PCX`, `ASE` to `XNYS`;
`BTS` and `CXI` to `XCBO`; `CMX` and `NYM` to `XNYM`; `FGI` and `SNP`, index
providers, to `XXXX`, ISO 10383's "no market"). `company_id` SHALL come from the
central index key of the symbol's latest Wikipedia version.

#### Scenario: A member resolves to a company
- **WHEN** `KO` is in the current list
- **THEN** `listing` has one row for `KO` whose `company_id` is the
  `company_id` of its central index key

#### Scenario: A member's market
- **WHEN** the latest Yahoo calendar row for `KO` has `exchange_code` `NYQ`
- **THEN** the `KO` listing has `market_code` `XNYS`

#### Scenario: A benchmark has no company
- **WHEN** a `portfolio` benchmark symbol is a market index
- **THEN** its `listing` row has an empty `company_id`

#### Scenario: A futures contract's market
- **WHEN** the latest Yahoo calendar row for `GC=F` has `exchange_code` `CMX`
- **THEN** the `GC=F` listing has `market_code` `XNYM`

#### Scenario: An index is not traded on a market
- **WHEN** the latest Yahoo calendar row for `^TRCCRB` has `exchange_code` `FGI`
- **THEN** the `^TRCCRB` listing has `market_code` `XXXX`, a row of `market`
