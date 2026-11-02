## 1. Series

- [x] 1.1 `src/common/fred_series.py`: add `CPIAUCSL`, `CPIAUCNS`, `CPILFESL` to
      `SERIES`; unit test that the list holds the seven series
- [x] 1.2 `uv run python -m pytest tests/common` passes; `databricks bundle validate`
- [x] 1.3 `cicd/affected_units.py` for the branch lists `run_fred` only

## 2. Documentation

- [x] 2.1 `references/docs/registers/source_systems/fred.md`: the three series in
      "Series fetched", monthly dates, the yearly `reload=true` after February (D3)
- [x] 2.2 `references/docs/registers/data-sources.md` and CLAUDE.md "Sources": FRED
      also carries US CPI
- [x] 2.3 The macro-prices probes in `references/poc/macro-prices/` and the probes
      register (committed with the proposal)

## 3. Dev

- [x] 3.1 Draft PR (deploy-dev as the service principal), then
      `uv run python cicd/run_dev.py fred --profile DEFAULT --param verify=true`
- [x] 3.2 `silver_landing.fred__observations` holds the three series with
      `frequency` `Monthly`, first and last dates and row counts as probe P2 (plus
      any newer month); the four rate series' counts unchanged apart from new days
- [x] 3.3 A second run writes only the recent rows (about 3 per CPI series)
- [ ] 3.4 Mark the PR ready; after merge, check the prd run of `run_fred` and the
      same counts in `mdp_prd`; archive
