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
- [x] 3.2 prd: same (run SUCCESS 2026-10-22; row count equals backup); restamp check superseded by D9
- [ ] 3.3 Drop `charity_register_scd2_backup` in dev and prd: done by the `reset` task (6.3), approved 2026-10-23

## 5. Back to standard Auto CDC (design.md; blocks archive and other sources)
- [x] 5.1 P5: snapshot Auto CDC without `ingested_timestamp` writes 0 rows on an unchanged run
- [x] 5.2 P6: function source with raw's fetch time as version
- [x] 5.3 P7: Landing from the change feed gets only changed rows
- [x] 5.4 P8: streaming Auto CDC from raw (stop if raw cannot be streamed)
- [x] 5.5 Decided 2026-10-23 (D7 to D9); proposal.md and spec rewritten
- [ ] 5.6 Silver Normalised: revisit with the user after 5.5

## 6. Bronze full pattern (implement PR)
- [ ] 6.1 Bronze SCD2 back in the bronze pipeline: P6's function source, own flow name, change data feed on, `pipelines.reset.allowed=false`
- [ ] 6.2 Landing: `ingested_timestamp = __START_AT`; verification checks the platform columns on Landing, not the SCD2 table
- [ ] 6.3 `run_acnc`: one-off `reset` task replaces `migrate`; remove the `scd2_merge` task; delete `src/common/scd2_merge.py` (and its test), `src/layers/bronze/scd2_merge.py`, `migrations/acnc_platform_timestamps.py`
- [ ] 6.4 Guard test allows `current_timestamp()` only in `_raw` files, the Landing stream and the stamping helpers
- [ ] 6.5 NAMING.md, patterns register (`bronze_publish_scd2_autocdc_full_load_python`, stated as the bronze full pattern), `design_patterns.yml`, CLAUDE.md acnc entry
- [ ] 6.6 dev: run `run_acnc` twice; first loads every row, second writes 0 rows to the SCD2 table and Landing; Landing equals a full read of the SCD2 table
- [ ] 6.7 prd: same, through the prd gate

## 4. Docs
- [x] 4.1 NAMING.md timestamp section, silver.md, decision register, patterns register, `design_patterns.yml`
- [ ] 4.2 At archive: update `pipeline-per-layer` (acnc's silver pipeline holds Landing only; Normalised is a job task)
