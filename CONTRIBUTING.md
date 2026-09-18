# Contributing

Workflow conventions for this repo — followed the same way whether a change is written
by a person or an AI coding agent.

## Branching

Create branches as `feature/<short-kebab-case-description>` (e.g.
`feature/phase2-dab-cicd`).

## Commits

Conventional-style prefixes — `feat:`, `fix:`, `chore:`, `docs:`, `refactor:` — one-line
summary in the present tense, explaining why over what where the diff itself doesn't
already make that obvious.

## Pull requests

Every change lands via PR. `main` is squash-merged only — branch protection requires
linear history, so no merge commits, no force push, no deletion of `main`.

## Cross-repo dependencies

OpenSpec has no cross-repo linking — each repo's `openspec/` only sees its own
changes. When a change in this repo depends on, or is depended on by, a change in
`demo-databricks-iac` (or vice versa), say so explicitly in `proposal.md` under a
`## Cross-repo dependencies` heading: the other change's ID, its repo, and which
direction the dependency runs (e.g. "Depends on `phase3a-neon-uc-connection` in
`demo-databricks-iac` — this change's ingestion pipeline references the `neon_dev`
UC Connection that one creates"). Plain text, not tooling — grep-able is the goal.

## Verification vs validation

These two words mean different things in this repo — don't use them
interchangeably:

- **Validation** is `databricks bundle validate` (or the `validate` job in
  `pr.yml`): static YAML/schema correctness, checked before deploy, no live
  environment touched.
- **Verification** is `verification/` — Databricks notebooks that check a
  *deployed* feature actually works against real (or synthetic) data: connection
  liveness, row-count parity, referential integrity, and similar. Chained into a
  job per pattern (e.g. `verify_neon_ecommerce_pattern`) so the whole thing can be
  re-checked on demand, not just proven once at implementation time. Kept separate
  from `tests/`, which is pytest against `src/common/` only, with no live-environment
  or network dependency.

## Comments

Default to no comments — clear naming should carry most of the load. Add one only
where the *why* isn't visible from the code itself: a behavior enforced somewhere
else entirely (e.g. a GitHub Environment's approval rule, not the workflow YAML that
references it), a non-obvious constraint, or a deliberate trade-off a future reader
could otherwise "fix" by accident. Never comment what the code already says plainly.
