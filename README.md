# demo-databricks-mdp

Databricks modern data platform — ingestion, modeling, ML, GenAI, and Apps.

Conventions: `CONTRIBUTING.md` (workflow), `NAMING.md` (names), `CLAUDE.md` (sources
and operational notes). Infrastructure (catalogs, schemas, grants) lives in the
separate `demo-databricks-iac` repo.

## Setup

Step by step per operating system:
[Windows](references/docs/setup/windows.md) · [macOS](references/docs/setup/mac.md).

You need Git and the GitHub CLI, uv (Python), the Databricks CLI, Node.js 20+ (for
OpenSpec) and, optionally, Claude Code. Then:

```bash
uv sync && uv run pytest
databricks auth login --host <workspace-url> --profile DEFAULT
databricks bundle validate --target dev --profile DEFAULT
```

Do not run `databricks bundle deploy|run|destroy` locally: pull requests deploy dev
as the CI/CD service principal, and you run its copy with
`uv run python cicd/run_dev.py <unit> --profile DEFAULT` (`CONTRIBUTING.md`, step 4).
`config.json` picks the edition (`free` or `standard`); after changing it run
`uv run python cicd/apply_edition.py`.

CI needs, per GitHub environment (`dev`, `prd`): secrets `DATABRICKS_HOST`,
`DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET` for the service principal, and
required reviewers on `prd`.

### OpenSpec
Changes are proposed and archived with OpenSpec (`openspec/`). The repo is already
initialised; `openspec update` refreshes the generated commands after an upgrade. In
a new repo, run `openspec init` once and choose the AI tools to generate commands
for. The workflow: `/opsx:propose`, `/opsx:apply`, `/opsx:archive` (or
`openspec new change`, `openspec validate`, `openspec archive`).

### Claude Code (optional)
Run `claude` from the repo root. `.claude/settings.json` enables the `databricks`
plugin and a hook that refuses local bundle deploys; `.claude/skills` and
`.claude/commands/opsx` hold the OpenSpec skills and commands; `CLAUDE.md` is the
project memory the agent reads first.

### VS Code
- [Databricks VS Code extension — quickstart](https://github.com/databricks/databricks-vscode/blob/release-v2.17.2/packages/databricks-vscode/DATABRICKS.quickstart.md)
- [Databricks VS Code extension — docs (AWS)](https://docs.databricks.com/aws/en/dev-tools/vscode-ext)
