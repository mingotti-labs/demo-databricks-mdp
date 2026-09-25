# Contributing

Workflow conventions for this repo — followed the same way whether a change is written
by a person or an AI coding agent.

## Software development lifecycle

Every non-trivial change follows this sequence, whether driven by a person or an AI
agent. Skipping or reordering steps is how work gets lost or lands broken:

**Propose and implement are two separate PRs, not one.** They're allowed to
happen at genuinely different times — merging the proposal immediately makes
it durable and reviewable on `main` right away, rather than sitting as an
open PR that drifts against `main` while implementation is pending
(possibly for days or weeks).

1. **Branch and propose** — `feature/<short-kebab-case-description>` off
   `main` (see Branching below), then `openspec new change <name>` (or
   `/opsx:propose`) on that branch, producing `proposal.md`, `specs/`,
   `design.md`, `tasks.md`, committed as its own `propose:`-prefixed commit.
   Nothing lands directly on `main` — not even proposal-only artifacts.
   Before proposing, confirm the model for this session (see Model selection
   below), and record the model recommended for implementation in
   `proposal.md` under a `## Model` heading — `Sonnet` or `Opus`, plus a
   one-line reason.
2. **Push, open a PR, get it agreed, merge** — this PR contains only the
   proposal. Once reviewed and agreed (in the PR or in chat), squash-merge
   it — the change now lives on `main` under `openspec/changes/<name>/`,
   unimplemented (`openspec status --change <name>` shows incomplete
   artifacts). Its branch is deleted per step 8, same as any merged PR.
3. **Implement, whenever ready** — a **new** branch off the now-updated
   `main` (the original branch name is free again after step 2's cleanup —
   reuse it, or add a suffix if it's still in flight for some reason). Before
   the first task, the agent states the model in `proposal.md`'s `## Model`
   and the model it is running on, and asks the human to confirm or switch
   (`/model`). Work through `tasks.md`, committing incrementally (see Commits
   below). If a cross-repo dependency is discovered only now, update
   `proposal.md` in this same branch (see Cross-repo dependencies below).
4. **Validate and verify** — `databricks bundle validate` before every
   deploy; deploy to `dev`; run the change's `verification/` job against
   real data (see Verification vs validation below). Only mark a task
   complete once it's verified, not just implemented.
5. **Push and open a second PR** — this one for implementation, referencing
   the already-merged proposal/openspec change (see Pull requests below).
   Reference any cross-repo PR it depends on.
6. **Review and merge** — squash-merge only, once approved.
7. **Archive the openspec change** — `openspec archive <name>` after this
   PR merges, so `openspec/specs/` reflects the new baseline.
8. **Clean up local branches — only after a PR has actually merged**, for
   both the propose PR and the implementation PR. A branch being
   implemented, verified, and pushed is not the same as being merged —
   deleting a local branch before its PR merges jumps ahead of a step a
   human still needs to review and approve, even though the remote branch
   itself survives the deletion. `git branch -d <branch>` belongs after
   merge, never before.

## Model selection

Claude Code sessions on this repo use one of two models, chosen per change:

- **Sonnet** — the default for changes that repeat an established pattern: a new
  source following the phase3c–3j ingestion shape (fetch helper, `_raw`,
  snapshot-based SCD1/SCD2, verification job, matching schema/grants), mechanical
  doc/naming fixes, applying an already-agreed `design.md`.
- **Opus** — for changes that set a convention or need deep reasoning: new medallion
  layers or sub-layers (Silver Normalised, Domain, Marts), a proposal/design with no
  prior template, cross-repo design, debugging an unfamiliar runtime failure (e.g.
  `phase3b-neon-scd-modeling`'s streaming-vs-upsert issue).

When unsure, use Opus for propose and Sonnet for implement (`opusplan` in `/model`).
Switch up to Opus mid-change if the work stops fitting its template — a source with
no stable key, an unexpected file format, a failure the existing pattern doesn't
explain.

The agent cannot switch models itself; it asks, and the human runs `/model`.

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
