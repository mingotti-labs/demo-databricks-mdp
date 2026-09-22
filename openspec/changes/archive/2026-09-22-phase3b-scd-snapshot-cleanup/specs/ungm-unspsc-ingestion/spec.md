## MODIFIED Requirements

### Requirement: SCD1/SCD2 modeling, Python only
`unspsc_public_scd1` and `unspsc_public_scd2` SHALL exist in
`bronze_ungm_publish`, built via `create_auto_cdc_from_snapshot_flow`
against `unspsc_public_raw` directly — not streaming Auto CDC, since this
source is not append-only, and not an intermediate snapshot materialized
view, which is unnecessary (confirmed via a real run against Neon's
equivalent pattern). No SQL equivalent SHALL be built for this pattern.

#### Scenario: SCD tables match source row count on initial load
- **WHEN** the SCD pipeline is run after `unspsc_public_raw` is populated
- **THEN** `unspsc_public_scd1` and `unspsc_public_scd2` each have a row
  count matching `unspsc_public_raw` exactly
