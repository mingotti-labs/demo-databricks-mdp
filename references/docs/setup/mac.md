# Setup on macOS

Uses Homebrew (https://brew.sh). Run in Terminal (zsh).

## 1. Tools
```bash
brew install git gh uv node
brew tap databricks/tap && brew install databricks
curl -fsSL https://claude.ai/install.sh | bash   # Claude Code (optional)
```
Check:
```bash
git --version; gh --version; uv --version; databricks --version; node --version; claude --version
```

## 2. Repo
```bash
gh auth login
gh repo clone mingotti-labs/demo-databricks-mdp
cd demo-databricks-mdp
uv sync
uv run pytest
```

## 3. Databricks
```bash
databricks auth login --host <workspace-url> --profile DEFAULT
databricks bundle validate --target dev --profile DEFAULT
```
The profile is saved in `~/.databrickscfg`. Do not deploy or run the bundle locally;
see the README.

## 4. OpenSpec
```bash
npm install -g @fission-ai/openspec@latest
openspec --version
openspec list
```

## 5. Claude Code (optional)
```bash
claude
```
From the repo root. Accept the project's `databricks` plugin when asked (or `/plugin`).

## macOS gotchas
- **Apple silicon:** Homebrew lives in `/opt/homebrew`; if `brew` is not found after
  installing it, run the two `eval` lines the installer prints.
- **`npm install -g` permission errors:** use Homebrew's Node (above), not the
  system one, and do not use `sudo`.
