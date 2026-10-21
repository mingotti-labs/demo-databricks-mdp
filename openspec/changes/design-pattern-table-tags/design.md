## Decisions

- **One value per table.** A table can involve several patterns; the tag holds
  the one that decides its shape (ingestion for `_raw`, publish for SCD tables,
  quarantine for quarantine tables, landing for landing). Listing all would
  make the tag a second register.
- **Mapping file, not tags in pipeline code.** Pipeline decorators cannot set
  tags, and a single file is where a pattern rename is made once.
- **Rule plus overrides.** About 340 tables exist; the file maps a schema to a
  default pattern and lists only exceptions (quarantine, SCD1 vs SCD2 suffix).
- **Notebook asks Unity Catalog for the object type** (`tables get`/
  `information_schema.tables`) to choose `ALTER MATERIALIZED VIEW` vs
  `ALTER STREAMING TABLE`, instead of the mapping carrying it.
- **Private views are skipped** (they are not catalog objects).

## Probes (before implementing)

- **P1**: `ALTER STREAMING TABLE ... SET TAGS` on an SP-owned pipeline streaming
  table, run as the run-as principal, succeeds with no `APPLY TAG` grant
  (Silver Normalised proved it only for materialized views).
- **P2**: tags survive the next pipeline refresh (they did for silver).

## Resolved

- Key is `design_pattern`, no `mdp_` prefix (everything here is mdp, so it is redundant).
- Clickstream, neon and airroi join with their own run jobs.
- Pattern tables are tagged too, by a job in the patterns bundle.
