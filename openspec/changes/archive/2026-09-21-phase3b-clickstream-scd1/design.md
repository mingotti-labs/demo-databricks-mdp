## Context

See proposal.md - Why. This is the clickstream half of the same "history
via SCD in `_publish`" pattern `phase3b-neon-scd-modeling` built for Neon.
Unlike that change, there's no architectural surprise here — confirmed by
running both pipelines, not assumed from the Neon precedent.

## Goals / Non-Goals

**Goals:**
- SCD1 in both languages, matching every other pattern's dual-language
  treatment
- Confirm — not assume — that plain streaming Auto CDC works against an
  append-only source, as a direct contrast to Neon's upsert-maintained one

**Non-Goals:**
- SCD2 for clickstream — events don't have a "changed" state to version;
  SCD1 already captures everything meaningful
- Any change to the 8 raw-ingestion variant pipelines — this only reads
  from the canonical `web_events_raw` (Python, `addNewColumns`), not the 7
  reference-only variants

## Decisions

**Plain streaming Auto CDC, not snapshot-based, in both languages.**
`web_events_raw` is populated purely by Auto Loader inserts — no MERGE, no
in-place update ever happens to it. This satisfies streaming Auto CDC's
append-only requirement directly, so `create_auto_cdc_flow`
(Python)/`AUTO CDC INTO ... FROM STREAM(...)` (SQL) both work without the
snapshot-comparison workaround `phase3b-neon-scd-modeling` needed. Verified
by actually running both pipelines against real data, not inferred from
"clickstream is append-only, so it should work."

**`timestamp` backtick-quoted in the SQL `SEQUENCE BY` clause.**
`timestamp` is also a type name/literal prefix in Spark SQL; backtick-quoting
the column reference avoids any parser ambiguity. The Python version needs
no such care since `sequence_by="timestamp"` is a plain string argument, not
inline SQL.

## Risks / Trade-offs

None beyond what `phase3b-clickstream-volume`/`phase3b-clickstream-autoloader`
already accepted — this only adds a downstream read of an existing, already
-verified table.

## Migration Plan

Additive only. Deploy, run both pipelines against `dev`, confirm row counts
match `web_events_raw` exactly. Rollback: remove the two new resources;
nothing else depends on them.
