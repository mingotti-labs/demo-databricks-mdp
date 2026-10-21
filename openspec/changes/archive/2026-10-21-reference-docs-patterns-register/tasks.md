## 1. Move
- [x] 1.1 `git mv docs references/docs` as its own commit (pure rename)

## 2. Fix references
- [x] 2.1 Update `cicd/workflows/{free,standard}/pr.yml` (schema path, path filter), then run `uv run python cicd/apply_edition.py` to regenerate `.github/workflows/`
- [x] 2.2 Update the `$id` in `normalised-spec/schema.json`, code comments in `src/` and `verification/`, NAMING.md, CLAUDE.md, CONTRIBUTING.md, `.claude/skills/silver-normalised-propose/SKILL.md`, and any remaining `docs/` mention under `references/docs/`
- [x] 2.3 Search for `docs/` outside `references/`, `.git`, `.databricks` and the OpenSpec archive; none may remain

## 3. Register
- [x] 3.1 Write `references/docs/registers/design-patterns.md`: one entry per implemented pattern (ID, what, when to use, code location, sources, verified or documented only), derived from the code and CLAUDE.md
- [x] 3.2 In `data-sources.md`, replace each source's "Ingestion pattern" line with a "Design patterns" line linking the IDs; add a short pointer to the register in `references/docs` where docs are indexed (README or CLAUDE.md)

## 4. Verify
- [x] 4.1 `uvx check-jsonschema` against `references/docs/normalised-spec/schema.json`, `uv run python -m pytest`, `apply_edition.py --check`, `databricks bundle validate -t dev`
- [x] 4.2 Open the implementation PR; confirm its checks pass
