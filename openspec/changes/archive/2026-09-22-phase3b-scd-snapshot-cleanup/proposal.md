## Why

All snapshot-based Auto CDC flows (Neon's 4 tables, UNGM's UNSPSC) wrapped
their source in an intermediate `_snapshot` materialized view, following
the Databricks docs' example pattern literally without testing whether it
was actually required. A direct question ("why not use `_raw` directly,
and should this object even sit in `_publish`?") led to testing it for
real: `create_auto_cdc_from_snapshot_flow`'s `source` does not need to be a
dataset within the same pipeline's dataflow graph — pointing it directly at
the raw table works, is simpler, and eliminates the "should this
implementation-detail object be exposed in `_publish`" question entirely
by removing the object altogether. Also folds in a small, purely cosmetic
naming fix requested alongside this: dropping "ecommerce" from the two
remaining display names that still had it.

## What Changes

- All 5 snapshot materialized views removed
  (`customers_snapshot`/`products_snapshot`/`orders_snapshot`/`order_items_snapshot`
  in Neon, `unspsc_public_snapshot` in UNGM) — each SCD1/SCD2 flow's
  `source` now points directly at the raw table
  (`bronze_neon.customers_raw`, `bronze_ungm.unspsc_public_raw`, etc.)
- **Discovered mid-migration, not upfront**: switching `source` on an
  *already-run* snapshot flow whose source is a Streaming Table
  (`bronze_neon.customers_raw`/`products_raw`) caused spurious duplicate
  "no-op" version records for unchanged rows in the corresponding SCD2
  tables — confirmed via a real check (199 of 200 customers had identical
  field values across two "versions"). UNGM's `unspsc_public_scd2`, sourced
  from a Materialized View rather than a Streaming Table, was unaffected
  (0 duplicates). Fixed with a full refresh of the affected Neon SCD
  pipeline, then re-verified SCD2 history-tracking still works correctly
  with a fresh real update (a new customer, `id=3`, to isolate the test from
  the two previously-tested customers)
- Cosmetic rename: `seed_neon_ecommerce`'s and
  `verify_neon_ecommerce_pattern`'s deployed display names drop
  "ecommerce" (resource keys unchanged, matching every other safe-rename
  precedent in this project)

## Capabilities

### Modified Capabilities
- `neon-scd-modeling`: the snapshot-based Auto CDC requirement no longer
  requires an intermediate snapshot view
- `ungm-unspsc-ingestion`: same, for `unspsc_public_scd1`/`scd2`

## Cross-repo dependencies

None.

## Impact

- Removes 5 source files, no new ones
- Full refresh applied to the Neon SCD pipeline only (`dev`) — discards
  previously-demonstrated SCD2 history for `id=1`/`id=2` (re-proven fresh
  with `id=3` afterward); UNGM's SCD pipeline was not touched, already clean
- 2 display-name renames, no resource-key changes, no data impact
