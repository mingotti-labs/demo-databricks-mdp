## 1. Probes

- [x] 1.1 Probes P1 and P2 (2026-10-31): the CSV's key, dates, encoding and
      orphan segments; scripts and results in `references/poc/iso-mic/`, rows in
      the probes register

## 2. Fetch

- [x] 2.1 `src/common/iso10383.py`: download, decode bytes as UTF-8, rename the
      17 columns, fail when one is missing; unit tests on a trimmed CSV string
      (including a row with an accent and a missing-column failure)
- [x] 2.2 Bundle variable `iso10383_mic_url` in `cicd/databricks/free.yml` and
      `standard.yml`; `uv run python cicd/apply_edition.py`; the `bronze--iso`
      pipeline passes it in `configuration`

## 3. Tables

- [x] 3.1 `src/layers/bronze/iso/market_identifier_codes_raw.py`: Materialized
      View with `ingested_timestamp` and the licence table comment
- [x] 3.2 `src/layers/bronze/iso_publish/market_identifier_codes_scd2.py`:
      snapshot view without `ingested_timestamp`, SCD2 by
      `market_identifier_code`, reset not allowed, change data feed on
- [x] 3.3 `src/layers/silver/landing/iso/market_identifier_codes.py`: change feed
      into `silver_landing.iso__market_identifier_codes` with the four dates as
      DATE
- [x] 3.4 `verification/bronze_checks/iso.yml` and
      `verification/silver_landing_checks/iso.yml` list the table;
      `src/common/design_patterns.yml` needs no new entry (the iso layers already
      carry their patterns); the register tests pass

## 4. Verify in dev

- [x] 4.1 Re-read the table quota; stop and ask if above 476 (12 slots to add,
      stop line 488)
- [x] 4.2 Draft PR deploys to dev; `run_iso` as the service principal with
      `verify=true`: raw 2,889 rows (or the current count), 1,596 `OPRT`;
      Publish and Landing equal to raw; `XASX` has country `AU`, `XTKS` has
      operating market `XJPX`, `CSOB` keeps its accents; a market with an
      `expiry_date` has a DATE
- [x] 4.3 `verify_silver_landing` with an empty `source` verifies one more entity
      than before the change
- [x] 4.4 Results in design.md

## 5. Docs

- [x] 5.1 `references/docs/registers/data-sources.md` (iso entry), CLAUDE.md
      (the ISO 3166 entry gains the MIC table and the licence limit), the probes
      register; all tests pass (`uv run python -m pytest`)
- [x] 5.2 After the prd run: counts equal dev's; archive the change
