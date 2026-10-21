## 1. Probe
- [ ] 1.1 Run P1 and P2 on one acnc streaming table in dev; record the result in design.md

## 2. Mapping and notebook
- [ ] 2.1 `src/common/design_patterns.yml` for acnc, ungm, iso, geonames, nsw_spatial (schema defaults plus overrides)
- [ ] 2.2 `src/common/tag_design_patterns.py`, parameters `catalog`, `source`, `workspace_file_path`
- [ ] 2.3 Add key `design_pattern` to `silver/normalised/tag.py`

## 3. Jobs
- [ ] 3.1 Add task `tag_patterns` to `run_{acnc,ungm,iso,geonames,nsw_spatial}.job.yml` after the last pipeline task

- [ ] 3.2 `tag_patterns` job in `references/patterns/` for the `pattern_bronze` tables (mapping: `bronze_` + table name)

## 4. Tests and docs
- [ ] 4.1 pytest: every mapped ID is a heading in `design-patterns.md`; every mapped table exists in the bundle
- [ ] 4.2 Register note "Finding a pattern from a table"

## 5. Verify
- [ ] 5.1 Run each `run_<source>` in dev; `information_schema.table_tags` shows `design_pattern` on every published table
