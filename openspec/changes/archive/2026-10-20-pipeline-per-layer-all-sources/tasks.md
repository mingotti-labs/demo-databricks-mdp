## 1. Docs

- [x] 1.1 `docs/medallion/silver.md`: rewrite "Orchestration" (one silver pipeline per source holding Landing and, once normalised, Normalised; `run_<source>` runs it then `tag`; airroi pending) and the "Materialisation when Databricks Native" pointer; verify by reading the diff
- [x] 1.2 `docs/normalised-spec/README.md` step 5: the generic `pipeline.py` and the spec are added to the source's silver pipeline, the tag task to `run_<source>`; no orchestrating job; verify by reading the diff
- [x] 1.3 NAMING.md (template display names, neon exception) and CLAUDE.md clickstream entry (canonical flow vs template variants); verify by reading the diff

## 2. Template display names

- [x] 2.1 Rename the display names of clickstream's seven non-canonical Auto Loader pipelines to `bronze--template--autoloader--...` (D3); `clickstream_autoloader` and both SCD pipelines keep `clickstream`; verify `bundle validate` and that resource keys and table names are unchanged
- [x] 2.2 After the PR's dev deploy, verify the seven pipelines show the `template` names in dev with the same pipeline ids (in-place rename), and `ci/affected_units.py` reports no unit for this change

## 3. Post-merge

- [x] 3.1 After merge, verify tst/prd deploys succeed with the renamed display names and no unit run
