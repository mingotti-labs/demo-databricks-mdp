## REMOVED Requirements

### Requirement: Seed data
**Reason**: clickstream moves to the patterns bundle (`neon-clickstream-to-patterns`) to free table slots.
**Migration**: the generator job is in `references/patterns/`; see `pattern-sources`.

### Requirement: Later batches exercise schema evolution
**Reason**: clickstream moves to the patterns bundle.
**Migration**: the generator job keeps the same batches.

### Requirement: Auto Loader ingestion into bronze_clickstream
**Reason**: clickstream moves to the patterns bundle.
**Migration**: pattern `bronze_autoloader_add_new_columns_python` writes `pattern_bronze.autoloader_add_new_columns_python`.

### Requirement: New columns are ingested without a pipeline change
**Reason**: clickstream moves to the patterns bundle.
**Migration**: the behaviour is written up in the pattern file and checked by its verify job.

### Requirement: Files are not moved or deleted after ingestion
**Reason**: clickstream moves to the patterns bundle.
**Migration**: unchanged; the volume stays in `bronze_clickstream` (iac).

### Requirement: Standing verification suite
**Reason**: clickstream moves to the patterns bundle.
**Migration**: the pattern's verify job in `references/patterns/`.

### Requirement: Schema-evolution mode variants, both languages
**Reason**: all eight variants now live in the patterns bundle.
**Migration**: `references/patterns/src/bronze/autoloader_<mode>_<language>`.

### Requirement: Documented behavior sourced from official docs where not independently verified
**Reason**: clickstream moves to the patterns bundle.
**Migration**: the write-ups stay in the pattern files.

### Requirement: SCD1 modeling in bronze_clickstream_publish
**Reason**: the pattern is live in yahoo, rba and fred (`bronze_publish_scd1_autocdc_stream_python`).
**Migration**: read `src/layers/bronze/yahoo_publish/`; the SQL variant stays in the patterns bundle.
