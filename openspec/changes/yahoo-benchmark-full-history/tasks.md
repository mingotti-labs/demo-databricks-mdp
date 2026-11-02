## 1. Rule

- [ ] 1.1 `src/common/yahoo_market.py`: `FULL_HISTORY_START`, `plan(..., benchmarks)`;
      unit tests: a new benchmark loads from 1970-01-01 as a reload; a new non-benchmark
      loads one year; a benchmark with stored prices is fetched incrementally
- [ ] 1.2 `src/common/fetch_yahoo.py`: pass the current benchmark symbols (already read
      for the symbol list) to every `plan()` call
- [ ] 1.3 `verification/bronze_checks/portfolio.yml`: `benchmarks_raw` `reference_rows` 22
- [ ] 1.4 `uv run python -m pytest tests` passes; `databricks bundle validate`
- [ ] 1.5 `cicd/affected_units.py` for the branch: expect `yahoo` and `portfolio`

## 2. Documentation

- [ ] 2.1 Yahoo source system file and CLAUDE.md "Sources": a new benchmark loads its
      full history, the S&P symbols one year
- [ ] 2.2 Probe P6 in the probes register (committed with the proposal)

## 3. Dev

- [ ] 3.1 Draft PR (deploy-dev as the service principal);
      `run_dev.py portfolio --param verify=true` passes with 22 `benchmarks_raw` rows
- [ ] 3.2 Run `run_dev.py yahoo` once: the rule changes nothing for symbols with state
      (the 8 and the others are fetched incrementally); the new-benchmark path is proved
      by the unit tests and, in prd, by the first load
- [ ] 3.3 Mark the PR ready; after merge CI loads the 8 in prd; then run `run_investments`
      in prd by hand; check `mdp_prd`: first dates 1984 (`^SPGSCI`), 1994 (`^TRCCRB`),
      2000 (futures), 2006 (`DBC`, `GSG`), the `fetch_state` rows, markets `XNYM` 4,
      `XXXX` 2, `XNYS` 2; archive `yahoo-commodity-symbols` and this change
