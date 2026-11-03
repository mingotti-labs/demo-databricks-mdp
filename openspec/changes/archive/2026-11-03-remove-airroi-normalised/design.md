## Decisions

- **Remove, do not pause.** A paused layer keeps a spec and a job task that the next run
  would use to rebuild 7 tables. Removing it matches the state in dev.
- **Backup under `references/backups/airroi-normalised/`**, as for neon. `specs/` cannot
  hold it: `tests/common/test_normalised_spec.py` and `rebuild.py` treat every file there
  as live. The backup holds the spec, the full job file and the pattern entry.
- **Keep the Landing check and `verify_silver_landing` for airroi.** Landing stays.
- **Evidence for no readers:** `grep` of the repo (excluding archive) finds `silver_normalised_airroi`
  only in the job, the design-pattern register, the docs and a CI test fixture. The fixture
  in `tests/cicd/test_affected_units.py` is a miniature repo with its own airroi entries
  and does not change.
