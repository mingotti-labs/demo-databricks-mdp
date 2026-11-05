## 0. Housekeeping

- [x] 0.1 Tick task 6.3 in `openspec/changes/archive/2026-11-05-market-climate-dashboard/tasks.md` (user confirmed
      the prd dashboard on 2026-11-05). Check: the file has no open box.

## 1. Probe P1: can CI deploy a Genie agent?

- [x] 1.1 Minimal `resources/genie/market_climate.genie.yml` (one table `${var.catalog}.gold_analytics_gateway.monitor_daily_signal`,
      one text instruction, `users` `CAN_RUN`); push as a draft PR. Check: `deploy-dev` passes and
      `databricks genie get-space <id> --include-serialized-space` shows `mdp_dev.gold_analytics_gateway.monitor_daily_signal`
- [x] 1.2 Record P1 in design.md and `references/docs/registers/probes.md`, scripts and output under
      `references/poc/market-climate-genie/`. If it fails: stop, report, and propose the iac grant or the D1 alternative

## 2. One source for the queries (D2)

- [ ] 2.1 Move `queries.py` to `src/common/market_climate_queries.py` and `build_dashboard.py` to
      `src/common/market_climate_dashboard.py` with `build()`; update the probe scripts' imports. Check: the
      regenerated `src/dashboards/market_climate.lvdash.json` has no diff
- [ ] 2.2 `cicd/build_market_climate.py` (writes both files; `--check` fails on a difference) and a pytest
      comparing both `build()`s with the committed files. Check: `python -m pytest tests -k market_climate` passes

## 3. The agent (D3-D6)

- [ ] 3.1 `src/common/market_climate_genie_instructions.md` (D4)
- [ ] 3.2 `src/common/market_climate_genie.py`: tables and joins (D5), examples (D3), sample questions,
      benchmarks (D6), ids from the dataset names, every list sorted. Check: the builder writes
      `resources/genie/market_climate.genie.yml`; `databricks bundle validate` passes
- [ ] 3.3 P2: every generated example SQL and benchmark answer runs in dev with `${var.catalog}` = `mdp_dev`.
      Check: all SUCCEEDED, result saved under `references/poc/market-climate-genie/`

## 4. Check in dev

- [ ] 4.1 Push; `deploy-dev` passes; the dev agent shows the five tables, the instructions, the examples
- [ ] 4.2 P3: benchmark evaluation in dev; every question passes or the miss is explained and fixed (dev-only
      `CAN_MANAGE` for `users` if the evaluation needs it). Check: eval result saved
- [ ] 4.3 P4: the user asks the spec's three scenarios in the dev agent and confirms the answers
- [ ] 4.4 Open question: "Ask Genie" link on the dashboard if it is one field; otherwise noted for later

## 5. After merge

- [ ] 5.1 prd deploy creates the agent; `get-space` shows `mdp_prd.` table names
- [ ] 5.2 The user asks the three scenarios in the prd agent and confirms
- [ ] 5.3 Planning: story design marks change 5 done; memory updated
