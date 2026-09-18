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

## Comments

Default to no comments — clear naming should carry most of the load. Add one only
where the *why* isn't visible from the code itself: a behavior enforced somewhere
else entirely (e.g. a GitHub Environment's approval rule, not the workflow YAML that
references it), a non-obvious constraint, or a deliberate trade-off a future reader
could otherwise "fix" by accident. Never comment what the code already says plainly.
