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

- [ ] 3.1 Draft PR (deploy-dev as the service principal); run in order
      `run_dev.py portfolio`, `run_dev.py yahoo`, `run_dev.py investments --param verify=true`
- [ ] 3.2 `listing` has the 8 symbols with markets `XXXX` (2) and `XNYM` (4) and
      `XNYS` (2); `price_daily` holds each from the first date in the design table;
      verification passes with no new failure
- [ ] 3.3 A second `run_yahoo` fetches only recent days for the 8 symbols
- [ ] 3.4 Mark the PR ready; after merge and the CI run, run `run_yahoo` then
      `run_investments` in prd; check the same in `mdp_prd`; archive
