## Context

Findings from the survey (read-only):
- `docs/` is referenced from `pr.yml` (schema path and path filter, in
  `cicd/workflows/{free,standard}/pr.yml` and the generated
  `.github/workflows/pr.yml`), `normalised-spec/schema.json` (`$id`), code
  comments in `src/` and `verification/`, NAMING.md, CLAUDE.md,
  CONTRIBUTING.md, the `silver-normalised-propose` skill, and the
  `silver-normalised` spec. Docs link to each other by relative path, which
  survives the move.
- `data-sources.md` already has an "Ingestion pattern" line per source, so
  linking patterns extends something that exists.
- `.databricks/` holds local bundle caches that mention `docs/`; it is not
  tracked and is ignored.

## Decisions

- **Register next to the data-sources register**:
  `references/docs/registers/design-patterns.md`.
- **ID scheme**: `<layer>_<technology>_<variant>_<language>`, language last
  and omitted when agnostic. Auto CDC is split into stream and snapshot
  entries, because streaming fails against upserted sources (Neon) while
  snapshot works.
- **Document what exists, and mark the rest.** Entries come from code already
  in the repo and the CLAUDE.md findings; a variant that was never run is
  marked "documented only", as CLAUDE.md already says for the clickstream
  variants. The other ingestion options Databricks documents (Lakeflow Connect SaaS,
  database CDC, file and community connectors, streaming, Zerobus, Federation,
  sharing) have no code here and are also entries
  marked `documented only`, with the reason they were not used.
- **Replace, don't duplicate, the "Ingestion pattern" lines**, so there is one
  place to read a source's pattern.
- **Mechanical move first, content second**, as separate commits, so the move
  is a pure rename in the history.
- **Archived OpenSpec files are not edited**; they are history.

## Risks

- A missed reference breaks PR validation (the schema path). Mitigation: after
  the move, search for `docs/` outside `references/` and the archive, run the
  schema check locally, and run `apply_edition.py --check`.
- Pattern IDs may need adjusting while entries are written. Accepted: that is
  why changes 2 and 3 wait.
