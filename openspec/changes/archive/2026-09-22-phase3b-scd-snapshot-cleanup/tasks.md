## 1. Test the direct-raw approach

- [x] 1.1 Changed `customers_scd1.py` to `source="bronze_neon.customers_raw"`
      (dropping the `customers_snapshot` wrapper), deployed, ran against
      `dev` — `COMPLETED`, 200 rows, `id=1`'s previously-tracked update
      correctly reflected

## 2. Propagate to all snapshot-based flows

- [x] 2.1 Updated `customers_scd2.py`, `products_scd1.py`,
      `products_scd2.py`, `orders_scd1.py`, `order_items_scd1.py`
      (Neon) and `unspsc_public_scd1.py`, `unspsc_public_scd2.py` (UNGM) to
      point `source` directly at their raw tables
- [x] 2.2 Deleted `customers_snapshot.py`, `products_snapshot.py`,
      `orders_snapshot.py`, `order_items_snapshot.py` (Neon) and
      `unspsc_public_snapshot.py` (UNGM)
- [x] 2.3 `databricks bundle validate` passed for dev/tst/prd; deployed and
      ran both pipelines against `dev` — both `COMPLETED`

## 3. Diagnose and fix the source-switch data-quality issue

- [x] 3.1 Row counts looked plausible but weren't checked precisely at
      first (`customers_scd2` = 401, not immediately recognized as wrong).
      A direct check (group by all tracked columns, count duplicates)
      found 199 of 200 customers had spurious duplicate "versions" with
      byte-identical field values — confirmed via `id=18`'s two rows
      showing the exact same name/email/`updated_at`
- [x] 3.2 Confirmed the same pattern in `products_scd2`, and confirmed
      `unspsc_public_scd2` (UNGM) was NOT affected (0 duplicates) — the
      structural difference being Streaming Table (Neon) vs. Materialized
      View (UNGM) as the underlying source
- [x] 3.3 Presented the finding and proposed fix to the user; got explicit
      confirmation before proceeding (full refresh is a flagged "dangerous"
      operation per this project's conventions)
- [x] 3.4 Full-refreshed the Neon SCD pipeline (`--full-refresh`, whole
      pipeline, not selective) — confirmed clean afterward: all 6 tables
      back to exact expected row counts, 0 duplicate-field-value rows

## 4. Re-prove SCD2 history tracking on the clean baseline

- [x] 4.1 Updated a fresh customer (`id=3`, not previously touched) via a
      throwaway verification notebook, deleted after use
- [x] 4.2 Re-ran ingestion (CI/CD-SP-owned pipeline) then the Neon SCD
      pipeline (normal run, not full refresh)
- [x] 4.3 Confirmed `id=3` shows exactly two correctly-bounded versions
      (old email closed with `__END_AT`, new email active), 0 unexpected
      duplicates elsewhere, total row count 201 (200 + 1 genuine new
      version) — SCD2 history tracking confirmed correct on the new,
      simpler configuration

## 5. Cosmetic rename

- [x] 5.1 `seed_neon_ecommerce.job.yml`'s display name:
      `seed--neon--ecommerce--${target}` → `seed--neon--data--${target}`
- [x] 5.2 `verify_neon_ecommerce_pattern.job.yml`'s display name:
      `verify--neon--ecommerce--${target}` → `verify--neon--lakeflow--${target}`
      (matching the ingestion pipeline's own already-renamed pattern name)
- [x] 5.3 Resource keys unchanged on both; `databricks bundle deploy`
      confirmed "Updated" not "Created" for both

## 6. Documentation

- [x] 6.1 Noted the snapshot-removal and source-switch finding in
      CLAUDE.md's "Sources" entries for Neon and UNGM, and updated the
      repository-structure tree comments
