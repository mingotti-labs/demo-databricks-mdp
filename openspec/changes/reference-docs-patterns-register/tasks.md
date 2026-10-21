## 1. Move
- [ ] 1.1 `git mv docs reference/docs` as its own commit (pure rename)

## 2. Fix references
- [ ] 2.1 Update `cicd/workflows/{free,standard}/pr.yml` (schema path, path filter), then run `uv run python cicd/apply_edition.py` to regenerate `.github/workflows/`
- [ ] 2.2 Update the `$id` in `normalised-spec/schema.json`, code comments in `src/` and `verification/`, NAMING.md, CLAUDE.md, CONTRIBUTING.md, `.claude/skills/silver-normalised-propose/SKILL.md`, and any remaining `docs/` mention under `reference/docs/`
- [ ] 2.3 Search for `docs/` outside `reference/`, `.git`, `.databricks` and the OpenSpec archive; none may remain

## 3. Register
- [ ] 3.1 Write `reference/docs/registers/design-patterns.md`: one entry per implemented pattern (ID, what, when to use, code location, sources, verified or documented only), derived from the code and CLAUDE.md
- [ ] 3.2 In `data-sources.md`, replace each source's "Ingestion pattern" line with a "Design patterns" line linking the IDs; add a short pointer to the register in `reference/docs` where docs are indexed (README or CLAUDE.md)

## 4. Verify
- [ ] 4.1 `uvx check-jsonschema` against `reference/docs/normalised-spec/schema.json`, `uv run python -m pytest`, `apply_edition.py --check`, `databricks bundle validate -t dev`
- [ ] 4.2 Open the implementation PR; confirm its checks pass
