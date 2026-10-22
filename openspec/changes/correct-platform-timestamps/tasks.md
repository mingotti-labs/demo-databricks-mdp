## 1. Probes (dev)
- [x] 1.1 P1: dataset removal behaviour; record in design.md
- [x] 1.2 P2: SCD2 `MERGE` on a copy in `pattern_bronze_publish`
- [x] 1.3 P3: Normalised rebuild that keeps timestamps, on a copy
- [x] 1.4 P4: Landing from the change feed, on the P2 copy

## 2. Code
- [x] 2.1 `src/common/scd2_merge.py` (tested) and a bronze SCD2 merge notebook task in `run_acnc`
- [x] 2.2 Landing as a streaming table from the SCD2 change feed, stamping in the stream
- [x] 2.3 `src/common/keep_timestamps.py` (tested) and a Normalised notebook task reusing `transforms.py`
- [x] 2.4 Remove `charity_register_scd2` from the bronze pipeline and the Normalised tables from the silver pipeline; `run_acnc` chains bronze pipeline, SCD2 merge, silver pipeline (Landing), Normalised task, tags, verifications
- [x] 2.5 Guard test: no `current_timestamp()` outside `_raw` files and the stamping helpers

## 3. Migration (each drop needs explicit approval)
- [x] 3.1 dev: backup, recreate with backfill, run, verify
- [ ] 3.2 prd: same, after the PR merges and the prd gate is approved (run SUCCESS 2026-10-22; restamp and row-count checks pending)
- [ ] 3.3 Drop `charity_register_scd2_backup` in dev and prd (explicit approval)

## 5. Open question
- [ ] 5.1 P5: streaming Auto CDC for bronze SCD2 on a copy; record the result in design.md before other sources follow

## 4. Docs
- [x] 4.1 NAMING.md timestamp section, silver.md, decision register, patterns register, `design_patterns.yml`
- [ ] 4.2 At archive: update `pipeline-per-layer` (acnc's silver pipeline holds Landing only; Normalised is a job task)
