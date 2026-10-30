# Portfolio internal data

Company-owned data for the dividend portfolio story, not an upstream system. All
of it lives in one source (`portfolio`) as CSV files in the
`bronze_portfolio.s3_raw` volume.

- Master copy: `data/portfolio/*.csv`, committed and reviewed by PR. The run job
  `run_portfolio` copies each file to
  `/Volumes/<catalog>/bronze_portfolio/s3_raw/<name>/landing/<name>.csv` first
  (`src/common/copy_repo_files.py`), overwriting the previous copy.
- Files: `concept_mapping`, `predecessor_ciks`, `settings`, `risk_levels`,
  `target_mix` (columns and keys in `data/portfolio/README.md`).
- Raw is text as the file shows it; SCD2 in `bronze_portfolio_publish` keeps the
  dated history of every change; Silver Landing in `silver_landing.portfolio__*`.
- Real purchases are not committed. They will be dropped into prd's volume
  (story step 11) and are never overwritten by the copy step, which only copies
  the committed files.
- Editing a CSV in a deployed target's volume is pointless: the next run
  overwrites it. Change the file in the repo.
