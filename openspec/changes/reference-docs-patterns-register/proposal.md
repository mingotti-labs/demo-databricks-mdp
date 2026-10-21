## Why

Live implementations and ones built only to demonstrate a design pattern are
mixed together, and nothing records which pattern each source uses or which
code exists purely as a pattern reference. This is change 1 of 3 (see
Context): create the place for reference material and the register that names
the patterns, before any code moves.

## What Changes

- **`docs/` moves to `references/docs/`** (git move, history preserved), and
  every path that points into it is updated: `pr.yml` in both edition sources
  (the schema path and the path filter), the generated `.github/workflows/`,
  the `$id` in `normalised-spec/schema.json`, code comments, NAMING.md,
  CLAUDE.md, CONTRIBUTING.md, the `silver-normalised-propose` skill, and the
  `silver-normalised` spec.
- **New `references/docs/registers/design-patterns.md`**: one entry per design
  pattern implemented in this repo. Each entry has a technology-driven ID
  (`<layer>_<technology>_<variant>_<language>`, language last and omitted when
  agnostic), what it is, when to use it, where the code lives, which sources
  use it, and whether it was verified or only documented.
- **`references/docs/registers/data-sources.md`**: each source's existing
  "Ingestion pattern" line is replaced by a "Design patterns" line linking the
  pattern IDs it uses.
- Wording: the label is "design pattern", not "template".
- **Out of scope**: moving any code (change 2), the iac pattern schemas
  (change 3), renaming any resource key, schema or table, and the dev-vs-prd
  table differences.

## Capabilities

### New Capabilities
- `design-pattern-register`: a register of implemented design patterns, and
  the link from each data source to the patterns it uses.

### Modified Capabilities
- `silver-normalised`: the "Specs validated in CI" requirement names the
  schema path, which moves to `references/docs/normalised-spec/schema.json`.

## Model

Sonnet to propose and implement: a mechanical move plus a register written
from patterns that already exist in this repo. Switch to Opus if the pattern
list needs real design judgement rather than description.

## Context

Change 1 of 3. Change 2 moves pattern-only code into a nested bundle at
`references/patterns/`; change 3 adds pattern schemas in `demo-databricks-iac`.
Both are drafted only when their turn comes, since pattern IDs may shift while
this register is written.

## Impact

- ~40 path references across workflows, code comments and docs; pull-request
  spec validation must still pass against the moved schema.
- The root bundle already syncs `docs/` to the workspace; it will now sync
  `references/docs/` instead. No pipeline, job, table or schema changes.
- Archived OpenSpec files keep their old `docs/` paths as history.
