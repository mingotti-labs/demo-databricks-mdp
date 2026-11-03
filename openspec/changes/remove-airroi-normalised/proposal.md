## Why

The table quota is near its cap (about 483 of 500 after the dev drop, stop line 488). A
review of the two Silver Normalised specs found airroi's the thinner one: no bridges, no
prd copy, nothing reading it. The 7 dev tables of `silver_normalised_airroi` were dropped
by hand on 2026-11-03 (user approved). `run_airroi` still has a `normalised` task, so the
next dev run would rebuild them. This change removes the layer for airroi so the drop
stays.

## What Changes

- `run_airroi` loses its `normalised`, `tag` and `verify_silver` (Normalised) tasks.
  `tag_patterns` depends on `silver`; `verify_silver` runs `verify_silver_landing` for
  `airroi`, like `run_abs`.
- The one-off `reset` task keeps its name but its `also_drop` list loses the
  `silver_normalised_airroi.*` entries (the tables are gone).
- The airroi spec moves from `src/layers/silver/normalised/specs/airroi.yml` to
  `references/docs/normalised-spec/examples/airroi.yml`, a backup of how a second
  source was specified. The decisions stay in the archived `phase4d` change.
- `src/common/design_patterns.yml` loses `silver_normalised_airroi`.
- Docs: `data-sources.md` (airroi block), `design-patterns.md` used-by lists,
  `silver.md` pending-refactor sentence, the `normalised-spec` README example.
- Not in this change: airroi bronze and Landing (kept), acnc Normalised (kept), prd
  (never had airroi Normalised).

## Capabilities

### Modified Capabilities
- `silver-normalised`: airroi is no longer a normalised source.

## Impact

- Frees about 7 quota slots in dev (already dropped). No prd table changes.
- CI: `airroi` is opted out of auto run (`ci_auto_run: false`); the changed job still
  puts `airroi` in the affected set, which does not run it.
- Reversible: restore the spec file and the three job tasks, then run `run_airroi`.

## Model

Sonnet: file moves and a job edit, no new design.
