# rdm (not yet built)

A future Databricks app in this repo that matches source values to
authoritative datasets, with a human approving matches. Seeded from
`phase4c-silver-normalised-design-time`'s design.md; built by its own later
changes, starting from this document.

## Dependency direction

rdm depends on Silver Normalised; Silver Normalised never reads rdm. The
normalised spec has no `rdm` block. Only approved rdm decisions flow on,
into Silver Domain.

## What rdm consumes

- Every table tagged `mdp.layer = silver_normalised` and
  `mdp.entity_kind = extracted`, across all sources
- `rdm_proposed_match_key` on those tables, so `AUSTRALIA`, `Australia` and
  `AuStRaLiA` become one matching decision instead of three
- Each source's `value_lineage`, to show stewards where a value came from

## Two use cases

| Use case | When | Example | Authoritative dataset |
| --- | --- | --- | --- |
| Match | An external standard exists | `country` → ISO 3166 | Already landed: `silver_landing_iso.*`, `silver_landing_geonames.*` |
| Curate, then match | No external standard exists | `order_status` from sources A and B | Created in rdm: a steward, with gen AI suggesting clusters, builds the list from the union of source entities (e.g. `SHIPPED` covering A's `SHIPPED`/`Shipped` and B's `dispatched`); it is then owned in rdm and matched as in the first case |

## What rdm writes: `rdm.crosswalk`

| Column | Example |
| --- | --- |
| `source_system`, `entity`, `value` | neon, country, `AuStRaLiA` |
| `authoritative_dataset`, `authoritative_code` | iso_3166_1, AU |
| `match_method` | exact, rule, genai, steward |
| `confidence` | 0.97 |
| `status` | proposed, approved, rejected |
| `approved_by`, `approved_timestamp` | |

The crosswalk keys on the natural key (`source_system`, `entity`, `value`),
which is why Silver Normalised needs no surrogate keys. Only `approved`
rows flow to Domain. Exact and rule matches can auto-approve, leaving gen
AI only the long tail.

## Open for rdm's own changes

Everything else: app design, where `rdm.crosswalk` lives, approval
workflow, and how Domain consumes approved rows.
