## 1. Settings and mapping

- [x] 1.1 `data/portfolio/benchmarks.csv`: the 8 rows (design.md table), kinds
      `commodity_index`, `commodity_future`, `commodity_fund`, empty sector
- [x] 1.2 `src/common/investments.py`: `CMX` and `NYM` to `XNYM`, `FGI` and `SNP` to
      `XXXX`; unit test of the four entries
- [x] 1.3 `uv run python -m pytest tests/common` passes; `databricks bundle validate`
- [x] 1.4 `cicd/affected_units.py` for the branch: expect `portfolio` and
      `investments`, not `yahoo`

## 2. Documentation

- [x] 2.1 `data/portfolio/README.md` and the Yahoo source system file: the new kinds
      and symbols, `XXXX` for indexes
- [x] 2.2 CLAUDE.md "Sources" (Yahoo, Silver Domain investments findings)
- [x] 2.3 Probe P5 in the probes register (committed with the proposal)

## 3. Dev

- [x] 3.1 Draft PR (deploy-dev as the service principal); run in order
      `run_dev.py portfolio`, `run_dev.py yahoo`, `run_dev.py investments --param verify=true`
- [x] 3.2 `listing` has the 8 symbols with markets `XXXX` (2) and `XNYM` (4) and
      `XNYS` (2); `price_daily` holds about one year (about 250 days) of each, as the
      other symbols; verification passes with no new failure
- [x] 3.3 Skipped by decision (user, 2026-11-03): the fetch is unchanged and its incremental
      run is proven for 500+ symbols (prd 2026-11-02); the 8 new symbols took the same path
- [ ] 3.4 Mark the PR ready; after merge and the CI run, run `run_yahoo` then
      `run_investments` in prd; check the same in `mdp_prd`; archive
