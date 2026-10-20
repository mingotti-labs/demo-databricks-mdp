## Context

The quota counts tables per metastore. Measured per catalog: dev 223, prd 120,
tst 110. `samples` (28) and `system` (43) do not appear to count: the user
tables alone (454) match the email's 90%. Removing `tst` brings the total to
about 344. `dev` is the largest and is the next lever if more headroom is
needed; it is deliberately not touched here.

## Decisions

- **Folders over conditionals.** Each edition is a complete, readable file
  (workflow or bundle), not one file with branches. Standard is today's file
  moved verbatim; free is a trimmed copy. The cost is duplication between the
  two copies, accepted to avoid if/else logic in YAML.
- **Copy, not include.** `.github/workflows/` and a root `databricks.yml` are
  fixed locations the tools require, so a script copies the chosen edition
  there. Generated files are committed; `--check` in PR CI guards drift.
  Thin reusable workflows were rejected: more moving parts, path constraints.
- **Flat bundle names** (`standard.yml`, `free.yml`), so none can be mistaken
  for a bundle root. The CLI looks for `databricks.yml` upward from the
  working directory, so a differently named file is never discovered (to be
  confirmed with `bundle validate` during implementation). Relative paths in
  the file resolve from where it is copied to (the root).
- **`config.json` minimal**: `edition` and `environments` only. `environments`
  documents and cross-checks the bundle targets (the check fails if the
  bundle's targets differ from the list); it does not generate them.
- **Committed edition is `free`**, since that is where the repo runs today.
- **Rename `tests/ci` to `tests/cicd`** and update `pyproject.toml`
  `testpaths`, to mirror `cicd/`.

## Risks

- Hand edits to generated files: mitigated by the drift check and a
  CONTRIBUTING.md note.
- Workflow path filters reference `ci/**` and `databricks.yml`: they become
  `cicd/**`, `config.json`, and `databricks.yml` in both editions.
- `affected_units.py` is run from `main.yml` by path: both workflow editions
  point at `cicd/affected_units.py`.
- Existing `mdp_tst` tables: removal is destructive DDL and needs explicit
  approval. Likely route: `databricks bundle destroy -t tst`, which CLAUDE.md
  warns may fail on SP-owned resources; otherwise delete pipelines then drop
  schemas. Done as a separate, approved step after the implementation PR
  merges, not part of the tasks below.
- The `tst` GitHub Environment and `mdp_tst` catalog (iac repo) are left in
  place; harmless once nothing deploys to them.
