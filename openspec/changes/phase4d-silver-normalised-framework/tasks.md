## 0. Cross-repo

- [x] 0.1 In `demo-databricks-iac`, propose and implement
      `phase4d-silver-normalised-airroi-schema`: `silver_normalised_airroi`
      in all three catalogs with `silver_landing_airroi`'s grants; verify
      the schema exists in `mdp_dev` before task 4.1

## 1. Spec logic (pure Python)

- [x] 1.1 Add `pyyaml` with `uv add pyyaml`; write
      `src/common/normalised_spec.py`: `load_spec`, every cross-reference
      check in design.md, `match_key`, `drift`, platform-column constants
- [x] 1.2 Write `tests/common/test_normalised_spec.py`: `specs/airroi.yml`
      loads; one failing case per cross-reference rule; `match_key`
      (`Vitória da Conquista`, `  AuStRaLiA `, inner whitespace); `drift`
      for a new, a missing and an ignored column; verify `uv run pytest`
      passes and remove `test_placeholder.py` if it is now redundant

## 2. Pipeline

- [x] 2.1 Write `src/common/silver_normalised.py` (base, bridge, extracted,
      `value_lineage`, quarantine) and `src/layers/silver/normalised/pipeline.py`
      per design.md; verify `ruff check --ignore F821` and `ruff format`
- [x] 2.2 Add `resources/pipelines/silver_normalised_airroi.pipeline.yml`;
      verify `databricks bundle validate -t dev --profile DEFAULT`

## 3. Tag step, orchestration, verification

- [x] 3.1 Write `src/layers/silver/normalised/tag.py` and
      `resources/jobs/silver_airroi.job.yml` (landing → normalised → tag)
- [x] 3.2 Write `verification/verify_silver_normalised.py` with every check
      in design.md's Verification table, and
      `resources/jobs/verify_silver_normalised.job.yml`; verify bundle
      validate passes

## 4. Run on airroi in dev (one run at a time)

- [x] 4.1 Deploy to `dev`; run `silver_airroi`; verify it succeeds and
      `silver_normalised_airroi` holds `market_summary` (4),
      `market_metrics_all` (48), `country` (2), `region` (3), `locality`
      (4), `district` (1), `value_lineage`; record PyYAML, pickle-by-value
      and tag-grant findings in design.md
- [x] 4.2 Verify `locality` holds `Vitória da Conquista` with
      `rdm_proposed_match_key = 'VITORIA DA CONQUISTA'`, and every table's
      tags in `information_schema.table_tags`
- [x] 4.3 Run `verify_silver_normalised` for airroi; verify it passes
- [x] 4.4 Rerun `silver_airroi` with Landing unchanged; verify identical
      rows apart from `transformed_timestamp` (determinism) and that
      verification still passes

## 5. CI

- [ ] 5.1 Add the `normalised-specs` job to `.github/workflows/pr.yml`
      (schema validation + `uv run pytest`) and widen its `paths`; verify
      it runs green on this change's implementation PR

## 6. Docs

- [x] 6.1 `docs/medallion/silver.md`: Orchestration section describes the
      real job (no longer forward-looking); N3 row states that key columns
      are never split; link platform-column handling to the README
- [x] 6.2 `docs/normalised-spec/README.md`: platform columns, parent and
      attribute resolution, extracted-entity columns, cross-reference
      checks, v0.1 limits
- [x] 6.3 `docs/registers/data-sources.md`: airroi "Consumed by Silver
      Normalised"; `docs/decision-register.md`: one entry per design.md
      decision (framework and airroi)
- [x] 6.4 Run `openspec validate phase4d-silver-normalised-framework
      --strict`; verify every relative link added resolves
