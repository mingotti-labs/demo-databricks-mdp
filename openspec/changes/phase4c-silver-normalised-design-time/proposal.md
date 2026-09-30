## Why

Every onboarded source now has a Silver Landing table, but Landing is
deliberately shallow: source-aligned, one table per Bronze Publish entity,
no restructuring. The next Silver sub-layer, Silver Normalised, needs
judgement Landing never did: which columns share a domain (`billing_country`
and `ship_to_ctry` are both `country`), which attributes depend on which,
where a delimited list hides a repeating group. That judgement is a one-off
per source, so it belongs at design time, in a reviewed artefact, not in
every pipeline refresh.

The chosen approach is **gen AI at design time, deterministic rules at run
time**: an agent (Opus) profiles a source's Silver Landing tables and
proposes a declarative per-source YAML *normalised spec*, reviewed in that
source's propose PR; one generic Lakeflow pipeline then executes any spec
deterministically. Fuzzy value matching (`AuStRaLiA` → `AU`) is out of
this layer entirely: it belongs to rdm, a future downstream app, with a
human approving matches.

This change is the design-time half of the framework: everything the
agent needs to propose a source — rules, spec format, agent instructions
and the standard profiling job — so the agent can be tried on acnc with
real profile evidence before the generic pipeline exists. The run-time
half (generic pipeline, verification, CI) follows in
`phase4d-silver-normalised-framework`.

Alternatives considered (full comparison in design.md):
- Rules in markdown only, each source hand-coded: works, but every source
  is bespoke code and the rules are enforced only by review.
- `ai_query` inside the pipeline: rejected as non-deterministic, costly per
  refresh, and hard to verify or audit.

## What Changes

- `docs/medallion/silver.md`: new Silver Normalised section (purpose,
  terminology, characteristics, what fits / does not fit, materialisation,
  rules N1–N10) and a labelled "Agent instructions — Silver Normalised"
  subsection pointing to the prompt template. Surrogate-key deferral
  reworded to "beyond Silver Normalised (Domain or later)".
- `NAMING.md`: Silver Normalised row reworded (structural, values
  unchanged); new Silver Normalised table-naming rules (base entity keeps
  the Landing table name, extracted entity is the singular domain name,
  bridge is `{parent}_{attribute}`, plus `value_lineage`); `_quarantine`
  widened beyond bronze; timestamp rules for aggregated entities.
- New `docs/normalised-spec/schema.json` (JSON Schema v0.1 for the
  normalised spec) and `docs/normalised-spec/README.md` (meaning of every
  attribute, extension rules, "Adding a source" steps).
- New `docs/templates/silver-normalised-propose.prompt.md` (the single copy
  of the design-time agent's instructions) and
  `docs/templates/silver-normalised-design.md` (skeleton for a source
  change's `design.md`).
- New `.claude/skills/silver-normalised-propose/SKILL.md`, a thin wrapper
  that loads the prompt template; `docs/skills/README.md` updated to list it.
- New `docs/component/rdm/README.md`, seeded from design.md's rdm section
  (context only; rdm is not built here).
- New standard profiling notebook and job
  (`src/layers/silver/normalised/profile.py`,
  `resources/jobs/profile_silver_normalised.job.yml`): profiles one
  source's Silver Landing tables and returns the evidence as JSON run
  output, which the agent saves into the source's openspec change.
- `docs/decision-register.md`: one entry per decision in design.md.
- No pipeline or Terraform change; the profiling job is the only new
  bundle resource.

## Capabilities

### New Capabilities
- `silver-normalised`: the Silver Normalised layer contract — source-aligned
  3NF restructuring of Silver Landing into base, bridge and extracted
  entities, rules N1–N10, tagging, timestamps, and the requirement that
  every source is driven by a reviewed normalised spec.

### Modified Capabilities
(none — `silver-landing`'s "No generated surrogate key" requirement does
not name the sub-layer surrogate keys are deferred to; only `silver.md`'s
prose does, and that is project documentation, not a tracked capability)

## Cross-repo dependencies

None for this change. Each later per-source change
(`phase4e-silver-normalised-acnc` onwards) depends on a
`silver_normalised_{source}` schema and grants change in
`demo-databricks-iac`.

## Model

Opus — new medallion sub-layer with no prior template (per CONTRIBUTING.md's
model selection); the prompt template and rules set the convention every
later source change follows.

## Impact

- Affected docs: `docs/medallion/silver.md`, `NAMING.md`,
  `docs/decision-register.md`, `docs/skills/README.md`.
- New docs: `docs/normalised-spec/`, `docs/templates/`,
  `docs/component/rdm/`.
- New repo-local skill: `.claude/skills/silver-normalised-propose/`.
- New code and bundle resource: the profiling notebook and job, deployed to
  `dev` and run once against acnc to verify. It only reads
  `silver_landing_{source}` tables and writes nothing to any table.
- Governed tags (tag policies enforcing allowed values) are out of scope;
  plain Unity Catalog tags are used, and governed tags go to the
  `demo-databricks-planning` roadmap backlog for discussion once Silver
  Normalised is finalised.
- Introduces a precondition for later source changes: a source's Landing
  tables must carry `ingested_timestamp` before it is normalised. Five
  sources (neon, clickstream, ungm, acnc, nsw_spatial) do not yet; each is
  retrofitted just in time, in its own change, before its Normalised
  proposal (acnc first, before `phase4e`).
- No breaking changes.
