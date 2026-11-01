## REMOVED Requirements

### Requirement: SCD1 for all four Neon tables, both languages
**Reason**: The Neon Bronze Publish tables are removed from the live bundle to
free table slots in the Free Edition metastore (500-table cap); nothing
downstream reads them. The Python SCD1 flow stays as a reference in the patterns
bundle (`bronze_publish_scd1_autocdc_snapshot_python`) and the SQL variant
already is one.
**Migration**: Restore from `references/backups/neon/` (`RECOVERY.md`).

### Requirement: SCD2 for customers and products only, both languages
**Reason**: Same: the Neon SCD2 tables are removed to free table slots. The
Python snapshot SCD2 flow moves to the patterns bundle as
`bronze_publish_scd2_autocdc_snapshot_python`; the SQL variant is
`bronze_publish_scd2_merge_sql`, already there.
**Migration**: Restore from `references/backups/neon/` (`RECOVERY.md`).

### Requirement: Snapshot-based Auto CDC, not streaming, in Python
**Reason**: The finding (streaming Auto CDC fails against an upserted source
with `DELTA_SOURCE_TABLE_IGNORE_CHANGES`) is kept in the design pattern register
entry `bronze_publish_scd2_autocdc_snapshot_python`, no longer as a requirement
of a live pipeline.
**Migration**: The register entry and the pattern's code comment.

### Requirement: skipChangeCommits is not an acceptable workaround
**Reason**: Documentation of a rejected option, moved to the pattern's register
entry with the rest of the finding.
**Migration**: The register entry.

### Requirement: SQL SCD2 runs as a job, not a pipeline dataset
**Reason**: The reference implementation already lives in the patterns bundle
(`pattern_bronze_publish_scd2_merge_sql`, register entry
`bronze_publish_scd2_merge_sql`); the Neon job copy is removed with the rest.
**Migration**: The patterns bundle job.
