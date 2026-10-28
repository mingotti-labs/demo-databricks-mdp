## Context

See proposal.md. The story design (`demo-databricks-planning`, revised
2026-10-25) puts all company-owned data in the `portfolio` source and the master
copies in this repo (user). The iac change created `bronze_portfolio.s3_raw` with
`READ_VOLUME`/`WRITE_VOLUME` for the CI/CD service principal and the user. The
closest existing source is `iso` (Materialized View, bronze full pattern,
change-feed Landing). Free Edition has dev and prd only.

## Goals / Non-Goals

**Goals:**
- One reviewed place (a PR) for every setting, and a dated history of each
  change, so a shortlist change can be traced to a threshold change.

**Non-Goals:**
- The purchases CSV (story step 11), the `reference` schemas (removed later in
  iac), typing the values (silver casts them), using the settings (later changes).

## Decisions

- **D1 Files in `data/portfolio/`.** A new top-level folder, deployed with the
  bundle (only `references/**` is excluded from sync). Rejected:
  `src/seed_data/` (that is synthetic data, these are real settings);
  `src/layers/bronze/portfolio/` (the pipeline's `libraries` glob would pick the
  files up as source).
- **D2 Copy step.** `src/common/copy_repo_files.py`, a notebook task first in
  `run_portfolio`, with parameters `source_glob` (the deployed
  `data/portfolio/*.csv`), `catalog`, `schema` and `volume`. Each file is copied
  to `<volume>/<name>/landing/<name>.csv` (NAMING.md "Volume paths"),
  overwriting. Generic: any source can reuse it. Only committed files match the
  glob, so real purchases dropped in the volume later are never touched (D7).
  Rejected: Auto Loader (the files are full snapshots, not new events); reading
  the workspace file directly from the pipeline (the volume is the agreed landing
  place and keeps the source shaped like a real file drop).
- **D3 CI selection.** The same `source_glob` string
  (`${workspace.file_path}/data/portfolio/*.csv`) is in the job's JSON, and
  `affected_units.py` maps every string naming repo files or globs, so a CSV edit
  selects `portfolio`. A unit test (`test_data_glob_in_a_job_parameter_names_the_data_files`)
  proves the resolver does it.
- **D4 Raw as text.** `spark.read.csv(path, header=True)` without schema
  inference: every column a string, as the file shows it; silver casts. Each
  `_raw` is a Materialized View with `ingested_timestamp`.
- **D5 Bronze full pattern per dataset**, as iso: private snapshot view without
  `ingested_timestamp`, SCD2 with `pipelines.reset.allowed=false` and change data
  feed. Natural keys:

  | Dataset | Key | Columns |
  |---|---|---|
  | `concept_mapping` | `figure`, `taxonomy`, `concept` | `figure`, `priority`, `taxonomy`, `concept` |
  | `predecessor_ciks` | `cik` | `cik`, `predecessor_cik`, `company`, `reason` |
  | `settings` | `setting` | `setting`, `value`, `currency_code`, `description` |
  | `risk_levels` | `level` | `level`, `sort_order`, `min_years_increases`, `max_payout_ratio`, `max_net_debt_to_ebitda`, `min_yield`, `max_yield`, `min_chowder`, `min_chowder_utilities`, `min_dividend_growth_5y` |
  | `target_mix` | `level` | `level`, `target_weight` |

  Empty cells mean "no rule". Ratios are fractions (`0.60`), not percentages.
- **D6 Starting values.** From the story design and the SEC probe (P5):
  - `concept_mapping`: the 11 figures and their candidate concepts in the order
    the probe tried them (`priority` 1 first); silver takes the latest annual
    value and uses `priority` only to break ties.
  - `predecessor_ciks`: `0002115436` (ExxonMobil Holdings Corp) to `0000034088`
    (Exxon Mobil Corp).
  - `settings`: `us_withholding_tax_rate` 0.15, `monthly_amount` 1000 AUD,
    `max_weight_per_company` 0.05, `max_weight_per_sector` 0.25,
    `pay_date_offset_days` 14 (KO, JNJ and O are 14 days in the probe).
  - `risk_levels` and `target_mix`: the story design's table (40/30/15/15).
  All are placeholders for the user to change by PR.
- **D7 Real purchases stay out of git.** The copy step copies only the named
  settings, so step 11 can drop real purchases into prd's volume without the
  copy ever overwriting or committing them.
- **D8 Silver Landing via `land_changes`**, one file per dataset in
  `src/layers/silver/landing/portfolio/`, own silver pipeline.
- **D9 New pattern** `bronze_volume_csv_materialized_view_python` in the register:
  a committed CSV copied to a UC volume by the run job and read by a Materialized
  View. Tagged on the five raw tables.
- **D10 Verification.** `bronze_checks/portfolio.yml` with each dataset's keys,
  columns and `reference_rows` (the committed row counts, known exactly), five
  Silver Landing entries, `portfolio` in `SOURCES_WITH_INGESTED_TIMESTAMP`.

## Risks / Trade-offs

- [`reference_rows` must change with every row added to a CSV] → accepted: the
  check then catches a file that did not copy; the unit test reads the same
  files, so a mismatch shows locally first.
- [A setting edited directly in the volume is overwritten on the next run] → by
  design: the repo is the master (user). Stated in the README of `data/portfolio/`.
- [The concept mapping is incomplete (NEE's capital expenditure)] → it is data:
  the SEC or silver change adds rows by PR.
- [The SEC bronze will read `bronze_portfolio` (first cross-source read in
  bronze)] → accepted in the story design; that change wires it.

## Migration Plan

Deploy to dev, run `run_portfolio` with `verify=true`, change one value, run
again and confirm one version closed and one inserted, then revert the value
(the revert run gives one more version, which is fine). prd: CI deploys on merge
and runs the unit. Rollback: remove the resources; the schemas and volume stay.

## Results (2026-10-25, dev)

- **First verified run** (`run_portfolio` with `verify=true`, every task
  succeeded, 15 tables tagged): the five volume files have the same content as
  the repo files (checksums equal). Raw, SCD2 current and Landing current rows:
  concept_mapping 35, predecessor_ciks 1, settings 5, risk_levels 4,
  target_mix 4.
- **A changed setting is versioned:** `monthly_amount` 1000 to 1200: `settings`
  went to 6 versions with 1 closed (values 1200 and 1000); the other four
  datasets stayed at 44 versions in total with 0 closed. Reverting to 1000 and
  running again gave 7 versions, 2 closed, as expected.
- A first `pytest` run failed because the new pattern was not yet in the
  register (a test checks every mapped pattern id is registered); fixed by
  task 4.1.
