## MODIFIED Requirements

### Requirement: Snapshot-based Auto CDC, not streaming, in Python
The Python SCD flows SHALL use `create_auto_cdc_from_snapshot_flow` against
the raw table directly (`bronze_neon.<table>_raw`), not
`create_auto_cdc_flow` (streaming) and not an intermediate snapshot
materialized view. `bronze_neon.*_raw` is upsert-maintained by Lakeflow
Connect, not append-only, so a streaming Auto CDC read against it fails;
`create_auto_cdc_from_snapshot_flow`'s `source` does not require a dataset
within the same pipeline's own dataflow graph — confirmed via a real run,
not assumed from the Databricks docs' example pattern (which happens to
show a wrapper view, but does not state one is required).

#### Scenario: Streaming Auto CDC against this source fails
- **WHEN** `create_auto_cdc_flow` (streaming) is used with
  `bronze_neon.customers_raw` as `source` and a real update has landed in
  that table
- **THEN** the flow fails with `DELTA_SOURCE_TABLE_IGNORE_CHANGES` —
  confirmed via a real run, not assumed

#### Scenario: Switching source on an already-run flow can pollute SCD2 history
- **WHEN** a snapshot-based Auto CDC flow's `source` is changed from an
  intermediate snapshot view to the raw Streaming Table directly, on a flow
  that has previously run under the old source
- **THEN** the next run may insert spurious duplicate versions with
  identical field values for rows that did not actually change — confirmed
  via a real occurrence (199 of 200 customers affected) — and a full
  refresh of the target is the fix, discarding prior history in the process
