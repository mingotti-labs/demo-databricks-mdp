# Portfolio settings

Curated settings for the dividend portfolio story, committed here and copied by
the `run_portfolio` job into `bronze_portfolio.s3_raw/<dataset>/landing/` on
every run. The repo is the master: a value edited in the volume is overwritten
on the next run. Every value is a placeholder to change by PR. Ratios are
fractions (0.15 is 15%); an empty cell means no rule.

| File | Key | What |
|---|---|---|
| `concept_mapping.csv` | `figure`, `taxonomy`, `concept` | SEC concepts to try for each fundamentals figure, `priority` 1 first |
| `predecessor_ciks.csv` | `cik` | Company ID to also fetch SEC facts for (reorganised companies) |
| `settings.csv` | `setting` | Tax rate, monthly amount, concentration limits, pay-date offset |
| `risk_levels.csv` | `level` | Thresholds of each risk level |
| `target_mix.csv` | `level` | Target share of the portfolio per risk level |
| `benchmarks.csv` | `symbol` | Funds and indexes to compare with (Yahoo symbols); `sector` matches Wikipedia's GICS sector |

Real purchases are not here and are never committed.
