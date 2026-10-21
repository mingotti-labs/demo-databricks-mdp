## Context

Surveyed (read-only):
- The seven variant pipelines exist in `dev` and `prd` (as
  `bronze--template--autoloader--...`) and own no tables: `mdp_dev` has only
  `web_events_raw` plus the two publish tables, and `mdp_prd` has no
  `bronze_clickstream` tables at all.
- Nothing outside the seven resource files, their source folders, CLAUDE.md,
  NAMING.md and the patterns register refers to the variants.
- The main bundle's `include` is `resources/**/*.yml`, so a bundle under
  `references/` is out of reach. Its workspace sync, by default, covers the
  whole repo, including `references/`.

## Decisions

- **Nested bundle, not a folder in the main bundle.** A folder under
  `resources/` would still deploy to prd. A second bundle with only a `dev`
  target cannot.
- **Correction to earlier thinking:** moving a resource to another bundle does
  not keep its identity; the resource is deleted from one deployment and
  created in the other. That is harmless here because the seven hold no data,
  but it is why the deletion is a manual pre-merge step and why the SQL twins
  (which own tables) wait.
- **Rename the resource keys to `pattern_<register ID>`.** Keys are normally
  never renamed, but these are new resources in a new bundle that was never
  deployed, so there is no identity to preserve. The key carries the pattern
  (`pattern_bronze_autoloader_rescue_python`), not the source system.
- **Group the pattern source by layer** (`src/bronze/`, later `bronze_publish/`
  and so on), each folder named after the register ID without the layer prefix.
- **Keep targeting `bronze_clickstream` for now.** The pattern schemas arrive
  in change 3; re-pointing is then a one-line change per pipeline with no data
  to migrate. Until then the variants are deployed but never run.
- **Display name segment `pattern`** replaces `template` for these pipelines
  and in NAMING.md/CLAUDE.md.
- **Manual deploy, no CI** for the patterns bundle initially: it is reference
  material in `dev`; the cost of CI exceeds the benefit.
- **`sync.exclude` lives in both edition sources** of the root
  `databricks.yml`, then `apply_edition.py` regenerates; the drift check
  guards it.

## Risks

- A forgotten deletion: a root deploy that would delete the seven pipelines
  stalls on the confirmation prompt. Mitigation: delete them in dev and prd
  first (listed in tasks), then merge; `bundle validate` and the PR deploy to
  dev check the result.
- Deleting a pipeline drops its tables: acceptable only because these have
  none. Verify with `tables list` immediately before deleting.
- The patterns bundle in a subfolder: running the CLI from inside it uses its
  own `databricks.yml`, which is intended; from the repo root, the root bundle
  is used, confirmed earlier for the renamed edition files.
