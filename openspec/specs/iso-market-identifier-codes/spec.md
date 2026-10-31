# iso-market-identifier-codes Specification

## Purpose
The ISO 10383 market identifier code list, ingested into the `iso` source up to
Silver Landing, as the reference for the markets a listing trades on.

## Requirements

### Requirement: Fetch helper
`src/common/iso10383.py` SHALL download the ISO 10383 CSV from the
`iso10383_mic_url` bundle variable, decode the response bytes as UTF-8 and
return rows keyed by these names: `market_identifier_code`,
`operating_market_identifier_code`, `operating_or_segment`, `market_name`,
`legal_entity_name`, `legal_entity_identifier`, `market_category_code`,
`acronym`, `country_code_alpha2`, `city`, `website`, `status`, `creation_date`,
`last_update_date`, `last_validation_date`, `expiry_date`, `comments`. It SHALL
fail when a source column is missing or renamed.

#### Scenario: Names keep their accents
- **WHEN** the helper reads the real file
- **THEN** the row for `CSOB` has `market_name` `ČESKOSLOVENSKÁ OBCHODNÍ BANKA, A.S.`

#### Scenario: A column is renamed upstream
- **WHEN** the source's header no longer has `MIC`
- **THEN** the helper fails and names the missing column

### Requirement: Raw table
`bronze_iso.market_identifier_codes_raw` SHALL be a Materialized View holding
every row of the file (operating markets and segments, active, updated and
expired), values as text, with `ingested_timestamp`, and a table comment that
names the ISO 10383 Registration Authority as the source and states that all or
a substantial part of the list must not be reproduced for third parties.

#### Scenario: A run lands the whole list
- **WHEN** the `bronze--iso` pipeline runs
- **THEN** the table has 2,889 rows (or the file's current count), 1,596 of
  them with `operating_or_segment` `OPRT`

### Requirement: Bronze Publish history
`bronze_iso_publish.market_identifier_codes_scd2` SHALL be SCD2 keyed by
`market_identifier_code` built by the bronze full pattern, with
`pipelines.reset.allowed` false and the change data feed enabled. A change to a
market's status or name SHALL close its version and open a new one.

#### Scenario: A market expires
- **WHEN** a later run reads `status` `EXPIRED` for a market that was `ACTIVE`
- **THEN** the old version has an end timestamp and a new current version has
  `EXPIRED`

#### Scenario: The key is unique
- **WHEN** the table is read after the first run
- **THEN** every `market_identifier_code` has exactly one current version

### Requirement: Landing table
`silver_landing.iso__market_identifier_codes` SHALL hold the current and past
versions with `ingested_timestamp` and `transformed_timestamp` set as for the
other `iso` Landing tables, `creation_date`, `last_update_date`,
`last_validation_date` and `expiry_date` as DATE (empty where the source is
empty), and every other value as text.

#### Scenario: Dates are dates
- **WHEN** a Landing row's source `expiry_date` is `20260928`
- **THEN** its `expiry_date` is the DATE 2026-09-28

#### Scenario: An open-ended market
- **WHEN** the source `expiry_date` is empty
- **THEN** the Landing `expiry_date` is null

### Requirement: Checks
The `iso` bronze checks file and Landing checks file SHALL both list the table,
and verifying with `source=iso` SHALL pass.

#### Scenario: Verification passes in dev
- **WHEN** `run_iso` runs in dev with `verify=true`
- **THEN** the raw, Publish and Landing row counts agree and the checks pass
