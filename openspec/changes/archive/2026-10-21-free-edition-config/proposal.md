## Why

Databricks warned that the metastore is at 90% of the 500-table Unity Catalog
quota. Measured (`system.information_schema.tables`): `mdp_dev` 223,
`mdp_prd` 120, `mdp_tst` 110, plus 1 in `dbacademy` = 454. The quota is per
metastore, so each environment multiplies every table. On Free Edition the
third environment (`tst`) is the cheapest to give up, but the repo must stay
usable unchanged on a paid edition.

## What Changes

- **Root `config.json`**: `{"edition": "free", "environments": ["dev", "prd"]}`.
  The single source of truth for what this deployment runs.
- **`ci/` renamed to `cicd/`**, holding everything edition-dependent:
  - `cicd/workflows/<edition>/*.yml`: the GitHub Actions workflows per edition.
  - `cicd/databricks/<edition>.yml`: the bundle file per edition
    (`standard.yml` is today's `databricks.yml` moved unchanged; `free.yml`
    drops the `tst` target).
  - `cicd/apply_edition.py`: reads `config.json` and copies the chosen files
    to `.github/workflows/` and the root `databricks.yml`. No other logic.
  - `cicd/affected_units.py` (moved from `ci/`) and its tests.
- **Generated files stay committed** (GitHub only runs `.github/workflows/`,
  the CLI only reads a root `databricks.yml`). A PR check runs
  `apply_edition.py --check` and fails on drift, so hand edits cannot survive.
- **Free workflows**: `main.yml` deploys `prd` straight after the approval
  gate, with no `deploy-tst` job.
- Docs: CONTRIBUTING.md note that the root `databricks.yml` and
  `.github/workflows/` are generated; CLAUDE.md and NAMING.md references to
  `ci/` and the three targets updated.
- **Out of this change**: removing the existing `mdp_tst` tables (destructive,
  needs explicit approval; see design.md) and the `mdp_tst` catalog itself
  (owned by `demo-databricks-iac`).

## Capabilities

### New Capabilities
- `edition-config`: how `config.json` selects the edition and how the
  edition-specific bundle and workflow files are applied and kept in sync.

### Modified Capabilities
- `ci-cd-pipeline`: the `tst` deploy requirement applies to the standard
  edition only; the free edition deploys `prd` after approval directly.

## Model

Sonnet to propose and implement. File moves, one small script and two
trimmed copies of existing files; no new convention beyond what is agreed here.

## Cross-repo dependencies

None required. Follow-up (not part of this change): `demo-databricks-iac`
still provisions `mdp_tst`; whether to remove it there is a separate decision.

## Impact

- Moves: `ci/` to `cicd/`, `tests/ci/` to `tests/cicd/`, `databricks.yml` to
  `cicd/databricks/standard.yml`, `.github/workflows/*.yml` to
  `cicd/workflows/standard/`. References updated in the workflows,
  `pyproject.toml` `testpaths`, CLAUDE.md, CONTRIBUTING.md.
- New: `config.json`, `cicd/apply_edition.py` with tests,
  `cicd/databricks/free.yml`, `cicd/workflows/free/`.
- Behaviour: with `edition: free` (the committed value) merges to `main` stop
  deploying to `tst`. No pipeline, job, or table definitions change.
- Projected table count once `mdp_tst` is cleaned up: about 344 of 500.
