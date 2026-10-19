## 1. Docs

- [ ] 1.1 `docs/medallion/silver.md`: rewrite "Orchestration" (one silver pipeline per source holding Landing and, once normalised, Normalised; `run_<source>` runs it then `tag`; airroi pending) and the "Materialisation when Databricks Native" pointer; verify by reading the diff
- [ ] 1.2 `docs/normalised-spec/README.md` step 5: the generic `pipeline.py` and the spec are added to the source's silver pipeline, the tag task to `run_<source>`; no orchestrating job; verify by reading the diff
- [ ] 1.3 NAMING.md (template display names, neon exception) and CLAUDE.md clickstream entry (canonical flow vs template variants); verify by reading the diff

## 2. Template display names

- [ ] 2.1 Rename the display names of clickstream's seven non-canonical Auto Loader pipelines and `clickstream_scd_modeling_sql` to `bronze--template--...` (D3); verify `bundle validate` and that resource keys and table names are unchanged
- [ ] 2.2 After the PR's dev deploy, verify the eight pipelines show the `template` names in dev with the same pipeline ids (in-place rename), and `ci/affected_units.py` reports no unit for this change

## 3. Post-merge

- [ ] 3.1 After merge, verify tst/prd deploys succeed with the renamed display names and no unit run
