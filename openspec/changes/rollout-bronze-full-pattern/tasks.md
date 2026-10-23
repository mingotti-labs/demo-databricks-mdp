## 1. Probes (dev)
- [x] 1.1 P1: change data feed on an existing pipeline-owned SCD2 table (ungm); Landing loads once
- [x] 1.2 P2: iso `subdivision_codes` writes 0 rows on an unchanged second load

## 2. Code (one source at a time; dev run after each)
- [x] 2.1 `migrations/reset_full_load.py` (parameterised, no-op once applied)
- [x] 2.2 ungm: change data feed, Landing as change-feed streaming table, `run_ungm` reset task and verification gate
- [x] 2.3 nsw_spatial: same
- [x] 2.4 iso: snapshot views without per-load columns, no stamping in the deduped view, Landing x2, reset
- [x] 2.5 geonames: same, Landing x4, reset
- [x] 2.6 Shared Landing code in `src/common/silver_landing.py` if the repetition warrants it

## 3. Verification
- [x] 3.1 `verification/verify_bronze.py` and `verification/bronze_checks/<source>.yml` for acnc, ungm, iso, geonames, nsw_spatial
- [x] 3.2 One job `verify--bronze--<target>` with a `source` parameter; remove the five per-source verify jobs and ten notebooks
- [x] 3.3 `verify` gate (parameter, condition task, `silver` with `run_if: NONE_FAILED`) on `run_acnc`, `run_ungm`, `run_iso`, `run_geonames`, `run_nsw_spatial`; silver Landing verification gated the same way
- [x] 3.4 Unit tests for the spec loader

## 4. Retries
- [x] 4.1 Both retry settings `"0"` on the 27 remaining pipelines (patch from `correct-platform-timestamps`)

## 5. Docs
- [x] 5.1 NAMING.md, patterns register, `design_patterns.yml`, CLAUDE.md, decision register, `data-sources.md`, source registers

## 6. Verify
- [x] 6.1 dev: ungm, nsw_spatial, iso and geonames each run twice (first load fills SCD2 and Landing, second load re-fetched and wrote 0 rows to both, one stamp per Landing table, ingested_timestamp = scd_valid_from_timestamp on every row), once with verify=true; the generic verify_bronze job passes for all five sources
- [ ] 6.2 prd: after merge, through the prd gate; acnc, ungm, iso, geonames, nsw_spatial all SUCCESS
- [ ] 6.3 Archive this change; archive `correct-platform-timestamps` first
