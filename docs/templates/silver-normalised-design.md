<!--
Skeleton for a Silver Normalised source change's design.md. Filled in by
the silver-normalised-propose agent (docs/templates/silver-normalised-propose.prompt.md).
Cite profile.json numbers for every claim; delete these comments.
-->

## Context

Source `{source}`; Landing tables and row counts from `profile.json`.
Precondition: `ingested_timestamp` present on every Landing table (step 0).

| Landing table | Rows | Columns | Natural key |
| --- | --- | --- | --- |
| | | | |

## Entities

<!-- Prompt steps 2-4. One row per table in silver_normalised_{source}. -->

| Entity | Kind (base / bridge / extracted) | From | Natural key | Rule(s) |
| --- | --- | --- | --- | --- |
| | | | | |

## Domains

<!-- Prompt step 2 (N7). Member columns and the evidence grouping them. -->

| Domain | Member columns | Evidence (distinct counts, value_overlaps) |
| --- | --- | --- |
| | | |

## Repeating groups

<!-- Prompt step 2 (N2). Omit the section if none. -->

| Bridge | Landing column(s) | explode / unpivot | Evidence (delimiter_rows, top_values) |
| --- | --- | --- | --- |
| | | | |

## Dependencies

<!-- Prompt step 3 (N3-N5). Every pair checked, including the ones not split. -->

| Table | Determinant → dependent | violating_values | Decision |
| --- | --- | --- | --- |
| | | | |

## Tolerances

<!-- Only if the spec declares dependency_tolerance. Reason per entry; the
exception rows go to {entity}_quarantine. Otherwise: "None". -->

## Ignored columns

<!-- Every ignored_columns entry and why it is left out. Otherwise: "None". -->

## Decisions

<!-- Judgement calls a reviewer should check first, with alternatives. -->

## Risks / Trade-offs

<!-- [Risk] → Mitigation -->
