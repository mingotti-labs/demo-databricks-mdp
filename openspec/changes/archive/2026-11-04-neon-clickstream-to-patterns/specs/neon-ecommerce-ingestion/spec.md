## REMOVED Requirements

### Requirement: Seed data
**Reason**: neon moves to the patterns bundle (`neon-clickstream-to-patterns`) to free table slots.
**Migration**: the seed job is in `references/patterns/`; see `pattern-sources`.

### Requirement: Query-based ingestion into bronze_neon
**Reason**: neon moves to the patterns bundle.
**Migration**: pattern `bronze_lakeflow_query_postgresql` writes `pattern_bronze.lakeflow_query_postgresql_<table>`.

### Requirement: Delete-blindness is a documented, accepted limitation
**Reason**: neon moves to the patterns bundle.
**Migration**: the limitation is documented in the pattern's register entry and README.

### Requirement: New source tables require an explicit pipeline change
**Reason**: neon moves to the patterns bundle.
**Migration**: documented in the pattern's register entry and README.

### Requirement: Standing verification suite
**Reason**: neon moves to the patterns bundle.
**Migration**: the pattern's verify job in `references/patterns/`.
