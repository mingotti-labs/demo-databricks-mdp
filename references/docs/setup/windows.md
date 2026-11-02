# Setup on Windows

Tested on Windows 11 with PowerShell 7 and Git Bash. Run the installs in PowerShell;
open a new terminal afterwards so `PATH` picks them up.

## 1. Tools
```powershell
winget install --id Git.Git -e            # Git, includes Git Bash (Claude Code needs it)
winget install --id GitHub.cli -e
winget install --id astral-sh.uv -e
winget install --id Databricks.DatabricksCLI -e
winget install --id OpenJS.NodeJS.LTS -e  # for OpenSpec
irm https://claude.ai/install.ps1 | iex   # Claude Code (optional)
```
Check:
```powershell
git --version; gh --version; uv --version; databricks --version; node --version; claude --version
```

## 2. Repo
```powershell
gh auth login
gh repo clone mingotti-labs/demo-databricks-mdp
cd demo-databricks-mdp
uv sync
uv run pytest
```

## 3. Databricks
```powershell
databricks auth login --host <workspace-url> --profile DEFAULT
databricks bundle validate --target dev --profile DEFAULT
```
The profile is saved in `%USERPROFILE%\.databrickscfg`. Do not deploy or run the
bundle locally; see the README.

## 4. OpenSpec
```powershell
npm install -g @fission-ai/openspec@latest
openspec --version
openspec list
```

## 5. Claude Code (optional)
```powershell
claude
```
From the repo root. Accept the project's `databricks` plugin when asked (or `/plugin`).

## Windows gotchas
- **Git Bash rewrites paths.** Arguments starting with `/` (for example
  `/Volumes/...` or `/Workspace/...` passed to the Databricks CLI) are turned into
  Windows paths. Prefix the command with `MSYS_NO_PATHCONV=1`, or run it in
  PowerShell.
- **`uv run python` wants Windows-style paths** for a script outside the repo:
  `C:/Users/<you>/...`, not `/c/Users/<you>/...`.
- **Line endings.** Git may warn "LF will be replaced by CRLF"; it is harmless. Keep
  `core.autocrlf` at its default (`true`).
- **Long paths.** If a clone fails on long file names:
  `git config --global core.longpaths true`.
