## 1. Probes (dev)
- [ ] 1.1 P1: dataset removal behaviour; record in design.md
- [ ] 1.2 P2: SCD2 `MERGE` on a copy in `pattern_bronze_publish`
- [ ] 1.3 P3: silver rebuild that keeps timestamps, on a copy

## 2. Code
- [ ] 2.1 `src/common/scd2_merge.py` (tested) and a bronze SCD2 merge notebook task in `run_acnc`
- [ ] 2.2 `src/common/keep_timestamps.py` (tested) and a silver notebook reusing `land()` and `transforms.py`
- [ ] 2.3 Remove `charity_register_scd2` from the bronze pipeline and acnc's silver pipeline; `run_acnc` chains bronze pipeline, SCD2 merge, silver, tags, verifications
- [ ] 2.4 Guard test: no `current_timestamp()` outside `_raw` files and the stamping helpers

## 3. Migration (each drop needs explicit approval)
- [ ] 3.1 dev: backup, recreate with backfill, run, verify
- [ ] 3.2 prd: same, after the PR merges and the prd gate is approved

## 4. Docs
- [ ] 4.1 NAMING.md timestamp section, silver.md, decision register, patterns register, `design_patterns.yml`
- [ ] 4.2 At archive: update `pipeline-per-layer` (acnc's silver layer is a job)
