## 1. Probes (dev)
- [ ] 1.1 P1: change data feed on an existing pipeline-owned SCD2 table (ungm); Landing loads once
- [ ] 1.2 P2: iso `subdivision_codes` writes 0 rows on an unchanged second load

## 2. Code (one source at a time; dev run after each)
- [ ] 2.1 `migrations/reset_full_load.py` (parameterised, no-op once applied)
- [ ] 2.2 ungm: change data feed, Landing as change-feed streaming table, `run_ungm` reset task and verification gate
- [ ] 2.3 nsw_spatial: same
- [ ] 2.4 iso: snapshot views without per-load columns, no stamping in the deduped view, Landing x2, reset
- [ ] 2.5 geonames: same, Landing x4, reset
- [ ] 2.6 Shared Landing code in `src/common/silver_landing.py` if the repetition warrants it

## 3. Verification
- [ ] 3.1 `verification/verify_bronze.py` and `verification/bronze_checks/<source>.yml` for acnc, ungm, iso, geonames, nsw_spatial
- [ ] 3.2 One job `verify--bronze--<target>` with a `source` parameter; remove the five per-source verify jobs and ten notebooks
- [ ] 3.3 `verify` gate (parameter, condition task, `silver` also depends on `bronze`) on `run_acnc`, `run_ungm`, `run_iso`, `run_geonames`, `run_nsw_spatial`; silver Landing verification gated the same way
- [ ] 3.4 Unit tests for the spec loader

## 4. Retries
- [ ] 4.1 Both retry settings `"0"` on the 27 remaining pipelines (patch from `correct-platform-timestamps`)

## 5. Docs
- [ ] 5.1 NAMING.md, patterns register, `design_patterns.yml`, CLAUDE.md, decision register, `data-sources.md`, source registers

## 6. Verify
- [ ] 6.1 dev: each unit run twice; first loads everything, second writes 0 rows to SCD2 and Landing; Landing equals a full read of the SCD2 table; one run per unit with `verify=true`
- [ ] 6.2 prd: after merge, through the prd gate; acnc, ungm, iso, geonames, nsw_spatial all SUCCESS
- [ ] 6.3 Archive this change; archive `correct-platform-timestamps` first
