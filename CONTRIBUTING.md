# Contributing

Workflow conventions for this repo — followed the same way whether a change is written
by a person or an AI coding agent.

## Software development lifecycle

Every non-trivial change follows this sequence, whether driven by a person or an AI
agent. Skipping or reordering steps is how work gets lost or lands broken:

1. **Propose** — `openspec new change <name>` (or `/opsx:propose`), producing
   `proposal.md`, `specs/`, `design.md`, `tasks.md`. Get the proposal agreed before
   implementing against it.
2. **Branch** — `feature/<short-kebab-case-description>` off `main` (see Branching
   below).
3. **Implement** — work through `tasks.md`, committing incrementally (see Commits
   below). If a cross-repo dependency exists, record it in `proposal.md` now (see
   Cross-repo dependencies below).
4. **Validate and verify** — `databricks bundle validate` before every deploy; deploy
   to `dev`; run the change's `verification/` job against real data (see Verification
   vs validation below). Only mark a task complete once it's verified, not just
   implemented.
5. **Push and open a PR** — every change lands via PR (see Pull requests below).
   Reference the openspec change, and any cross-repo PR it depends on.
6. **Review and merge** — squash-merge only, once approved.
7. **Archive the openspec change** — `openspec archive <name>` after merge, so
   `openspec/specs/` reflects the new baseline.
8. **Clean up local branches — only after the PR has actually merged.** A branch
   being implemented, verified, and pushed is not the same as being merged —
   deleting a local branch before its PR merges jumps ahead of a step a human still
   needs to review and approve, even though the remote branch itself survives the
   deletion. `git branch -d <branch>` belongs after merge, never before.

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
