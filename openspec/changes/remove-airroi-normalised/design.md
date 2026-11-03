## Decisions

- **Remove, do not pause.** A paused layer keeps a spec and a job task that the next run
  would use to rebuild 7 tables. Removing it matches the state in dev.
- **Backup the spec as an example, not in `specs/`.** `tests/common/test_normalised_spec.py`
  and `rebuild.py` treat every file in `specs/` as live. The example folder keeps the
  airroi shape (a parent chain of extracted entities, two SCD2 base entities, no bridges)
  next to the schema documentation.
- **Keep the Landing check and `verify_silver_landing` for airroi.** Landing stays.
- **Evidence for no readers:** `grep` of the repo (excluding archive) finds `silver_normalised_airroi`
  only in the job, the design-pattern register, the docs and a CI test fixture. The fixture
  in `tests/cicd/test_affected_units.py` is a miniature repo with its own airroi entries
  and does not change.
