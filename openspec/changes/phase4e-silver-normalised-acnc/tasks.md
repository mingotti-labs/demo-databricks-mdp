## 0. Cross-repo

- [ ] 0.1 In `demo-databricks-iac`, propose and implement
      `phase4e-silver-normalised-acnc-schema` (`silver_normalised_acnc`,
      grants as `silver_normalised_airroi`); verify the schema exists in
      `mdp_dev` before task 4.1

## 1. Retrofit acnc `ingested_timestamp`

- [ ] 1.1 `charity_register_raw` stamps `ingested_timestamp`;
      `charity_register_valid` stamps `transformed_timestamp`;
      `charity_register_scd2` lists both in
      `track_history_except_column_list`
- [ ] 1.2 Add `acnc` to `verify_silver_landing.py`'s sources expected to
      carry `ingested_timestamp`; NAMING.md notes acnc is retrofitted
- [ ] 1.3 Deploy to `dev` (PR CI), run the SP chain (ingestion → SCD →
      Landing); verify every current Landing row has a non-null
      `ingested_timestamp`, record whether the SCD2 target needed a full
      refresh, and verify Silver Landing verification still passes

## 2. Framework corrections

- [ ] 2.1 `unpivot.columns` in `normalised_spec.used_columns`/`drift`,
      `transforms.bridge` and verification's bridge count; unit tests for a
      `columns` family and its drift
- [ ] 2.2 Null is not a value for parents: extracted entities use the one
      non-null parent; unit-testable rule stated in the README; verify on
      airroi that results are unchanged
- [ ] 2.3 Verification checks `ingested_timestamp` on current rows of SCD2
      base entities only
- [ ] 2.4 Prompt template and README: step 0 (retrofit in its own change
      or as the source change's first tasks), pass 2 on full data for
      row-limited sources, current-rows timestamp rule

## 3. acnc resources

- [ ] 3.1 `resources/pipelines/silver_normalised_acnc.pipeline.yml` and
      `resources/jobs/silver_acnc.job.yml` (landing → normalised → tag);
      verify `bundle validate`

## 4. Run on acnc in dev (SP-owned, one run at a time)

- [ ] 4.1 Run `silver_acnc`, then `verify_silver_normalised` for acnc;
      verify both pass, with bridge row counts equal to the profile's flag
      and list-element counts
- [ ] 4.2 Rerun `verify_silver_normalised` for airroi; verify it still
      passes after the framework corrections

## 5. Docs

- [ ] 5.1 `docs/registers/data-sources.md` (acnc "Consumed by Silver
      Normalised"), `docs/decision-register.md` (one entry per design.md
      decision and correction), CLAUDE.md (acnc dev loads the full dataset)
- [ ] 5.2 `openspec validate phase4e-silver-normalised-acnc --strict`;
      relative links resolve
