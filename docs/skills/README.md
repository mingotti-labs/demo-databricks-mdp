# Claude Code skills used on this project

What's actually installed and in use when an AI coding agent (Claude Code)
works on this repo — not a general Claude Code tutorial, just this
project's real setup, confirmed by inspecting the actual config files
rather than assumed.

## Global plugins (`~/.claude/settings.json`, `enabledPlugins`)

| Plugin | Used on this project? |
|---|---|
| `databricks` | **Yes — the primary one.** Also pinned again in this repo's own `.claude/settings.json`. Provides the `databricks-core`, `databricks-pipelines`, `databricks-dabs`, `databricks-lakeflow-connect`, and other product-specific skills (CLI usage, DAB/`databricks.yml` conventions, Lakeflow Spark Declarative Pipeline patterns) that every pipeline/bundle change in this repo goes through |
| `superpowers` | **Yes — `brainstorming` specifically.** Used to scope non-trivial work (spike vs. bounded vs. architectural) before committing to an approach |
| `context7` | Available, for up-to-date library/framework docs lookups — not project-specific |
| `code-review`, `code-simplifier` | Available for review/refactor tasks — not exercised heavily in this repo's own history yet |
| `frontend-design`, `ralph-loop` | Installed globally but **not relevant** to this repo — no frontend work here, and `ralph-loop` is an unrelated autonomous-loop workflow |

Versions confirmed in use during real work on this repo: `databricks` plugin
0.2.16, `superpowers` plugin 6.3.0 (both read from
`~/.claude/plugins/cache/claude-plugins-official/`, not assumed from a
changelog).

## Repo-local skills (`.claude/skills/`, `.claude/commands/opsx/`)

Not a plugin — these `openspec-*` skills and `/opsx` slash commands are
committed directly into this repo (and `demo-databricks-iac`, which has the
identical set), part of the OpenSpec tool's own project setup, not
Claude Code's global plugin system:

- `openspec-explore`, `openspec-propose`, `openspec-update-change`,
  `openspec-apply-change`, `openspec-sync-specs`, `openspec-archive-change`
- These back this project's actual workflow (see CONTRIBUTING.md /
  CLAUDE.md's "Workflow" section): propose → validate --strict → implement
  → archive, used for every non-trivial change in this project's history

## Discovery: "Databricks AI Dev Kit" vs. the `databricks` plugin

Investigated 2026-09-24 after being asked whether components here were
built using "Databricks AI Dev Kit" skills specifically.

**Finding**: `databricks-solutions/ai-dev-kit` was an earlier Field
Engineering toolkit that used to bundle its own bundled skill files. Its own
README now states those bundled files are deprecated and kept for reference
only — the actual skills moved upstream to `databricks/databricks-agent-skills`,
delivered via `databricks aitools install`. That upstream/CLI-installed path
is exactly what the `databricks` Claude Code plugin (in the table above)
already provides — confirmed by fetching the ai-dev-kit repo directly, not
assumed from its name alone.

So for the skill layer specifically, this project was already using the
current successor to "ai-dev-kit," under its new name, not a separate or
outdated thing.

**What ai-dev-kit has that isn't part of this setup**, if ever needed:
- A **Builder App** (local/Databricks-hosted chat UI; can also run as an
  MCP server)
- A standalone **MCP server** (`databricks-mcp-server`, 40+ Databricks
  tools exposed directly via MCP instead of the CLI-driven skill workflow
  used here)
- A `databricks-tools-core` Python library for programmatic use in code

None of these were installed or used for this project as of this note —
purely CLI + skills, per the table above.
