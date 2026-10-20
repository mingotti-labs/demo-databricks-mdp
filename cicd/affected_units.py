"""Decide which runnable units a change affects, so CI runs those and nothing else.

Why this exists
---------------
``databricks bundle deploy`` only reports changes to resource *configuration*.
A commit that edits shared Python (say ``src/common/normalised_spec.py``)
deploys as "0 changed" yet changes the behaviour of every pipeline importing
it. CI therefore cannot ask the deploy what to run. It asks this module.

Vocabulary
----------
resource
    A pipeline or a job defined in the bundle, identified by the pair
    ``(type, key)``, e.g. ``("pipelines", "acnc_charity_register_ingestion")``.
unit
    A job whose resource key starts with ``run_`` (``run_acnc`` is the unit
    ``acnc``). A unit is the thing CI runs, with ``databricks bundle run``.
    It is a source today and may be a silver or gold domain tomorrow; the
    lookup does not care which. A unit tagged ``ci_auto_run: "false"`` is never
    selected (paid-API sources).
bundle JSON
    The output of ``databricks bundle validate -t <target> -o json``: every
    resource fully resolved for one target (variables substituted, relative
    paths turned into workspace paths under ``workspace.file_path``).

The algorithm
-------------
Inputs: the bundle JSON at the base and head commits, the files changed
between them, the repo's tracked files, and a way to read a file's source.

1. Config changes. A resource is *affected* if it exists at head and is
   missing at base or its resolved JSON differs. This catches edits to its
   YAML, to ``databricks.yml`` variables it uses, and brand-new resources.
2. File changes. For each resource, collect the repo files it *uses*:
   every string anywhere in its JSON that names a tracked file (a pipeline
   ``libraries`` entry, a job notebook, a config value such as
   ``normalised_spec: src/.../acnc.yml``). Globs such as ``src/x/**`` are
   expanded, and a notebook path without ``.py`` matches ``<path>.py``.
   Then follow imports: each used ``.py`` file is parsed with ``ast`` and
   every ``src/`` module it imports is added, repeatedly, until nothing new
   appears. A resource is *affected* if any file in that closure changed.
3. Reach. A unit reaches its own job, every ``pipeline_task`` pipeline and
   every ``run_job_task`` job (and what those reach). The references are the
   unresolved ``${resources.<type>.<key>.id}`` strings in the JSON.
4. Selection. A unit is selected when it reaches an affected resource and is
   not opted out. If nothing is selected, nothing runs. That is deliberate:
   this is CI/CD, not orchestration.

Worked example (the ``phase4e`` shared-code commit)
---------------------------------------------------
The commit changed ``src/common/normalised_spec.py`` and
``src/layers/silver/normalised/transforms.py``; no YAML. Step 1 finds
nothing. Step 2: ``silver_normalised_acnc`` uses ``pipeline.py`` (its
``libraries``), which imports ``layers.silver.normalised.transforms``, which
imports ``common.normalised_spec``; both changed, so the pipeline is
affected. The same holds for ``silver_normalised_airroi`` and for every job
running ``tag.py``. Step 3: ``run_acnc`` runs ``silver_normalised_acnc``
(a ``pipeline_task``) and ``tag.py``. Step 4: ``acnc`` is selected;
``airroi`` is affected but opted out, so it is reported as skipped.

What is not detected (by design)
--------------------------------
* A file read through a hardcoded path that no bundle config mentions.
* Relative imports (``from . import x``); the repo uses absolute imports
  rooted at ``src/`` only.
* Data dependencies between units (a gold domain reading a silver table).
  Give the downstream unit's job a ``run_job_task`` on the upstream job and
  step 3 follows it.
Changed files under ``src/`` or ``verification/`` that no resource uses are
reported as *unattributed* so they are visible, never silently lost.

Adding a unit
-------------
Write ``resources/jobs/run_<unit>.job.yml`` chaining the unit's pipelines
and jobs; add ``tags: {ci_auto_run: "false"}`` to opt out. Nothing else:
there is no map to update.

Command line (CI)::

    python cicd/affected_units.py --target tst            # base = last success
    python cicd/affected_units.py --target dev --base <sha> --head <sha>

stdout: selected unit names, one per line. stderr / ``$GITHUB_STEP_SUMMARY``:
the base used, affected resources, skipped units, unattributed files.
"""

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

RESOURCE_TYPES = ("pipelines", "jobs")
UNIT_PREFIX = "run_"
OPT_OUT_TAG = "ci_auto_run"
SRC_ROOT = "src"
UNATTRIBUTED_PREFIXES = ("src/", "verification/")
REFERENCE = re.compile(r"\$\{resources\.(pipelines|jobs)\.([A-Za-z0-9_]+)\.id\}")

Resource = tuple[str, str]


@dataclass
class Result:
    """Outcome of one lookup."""

    units: list[str] = field(default_factory=list)
    skipped_units: list[str] = field(default_factory=list)
    affected_resources: list[Resource] = field(default_factory=list)
    unattributed: list[str] = field(default_factory=list)


def resources(bundle: dict) -> dict[Resource, dict]:
    """Return every pipeline and job of a bundle JSON, keyed by ``(type, key)``."""
    section = bundle.get("resources", {})
    return {
        (kind, key): body
        for kind in RESOURCE_TYPES
        for key, body in section.get(kind, {}).items()
    }


def discover_units(bundle: dict) -> dict[str, bool]:
    """Return ``{unit name: auto_run}`` for every ``run_`` job of the bundle.

    A unit auto-runs unless its job is tagged ``ci_auto_run: "false"``.
    """
    return {
        key.removeprefix(UNIT_PREFIX): body.get("tags", {}).get(OPT_OUT_TAG) != "false"
        for (kind, key), body in resources(bundle).items()
        if kind == "jobs" and key.startswith(UNIT_PREFIX)
    }


def changed_resources(base: dict, head: dict) -> set[Resource]:
    """Return resources new at head or whose resolved JSON differs from base."""
    before = resources(base)
    return {ref for ref, body in resources(head).items() if before.get(ref) != body}


def strings(value) -> Iterator[str]:
    """Yield every string found anywhere inside nested dicts and lists."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def repo_relative(value: str, file_path: str) -> str | None:
    """Turn a string from the bundle JSON into a repo-relative path, or None.

    Workspace paths under ``file_path`` (the deployed copy of the repo) have
    that prefix stripped. Other absolute paths, empty strings and unresolved
    ``${...}`` references are not repo paths.
    """
    prefix = file_path.rstrip("/") + "/"
    if value.startswith(prefix):
        return value[len(prefix) :]
    if value.startswith("/") or "${" in value or not value:
        return None
    return value


def glob_regex(pattern: str) -> re.Pattern:
    """Compile a repo glob: ``**`` crosses folders, ``*`` and ``?`` do not."""
    parts = {"**": ".*", "*": "[^/]*", "?": "[^/]"}
    tokens = re.split(r"(\*\*|\*|\?)", pattern)
    return re.compile("".join(parts.get(t) or re.escape(t) for t in tokens))


def matching_files(pattern: str, repo_files: list[str]) -> list[str]:
    """Return the tracked files a bundle path refers to.

    A path matches itself, itself plus ``.py`` (notebooks drop the suffix), or,
    when it contains wildcards, every file the glob matches.
    """
    if any(c in pattern for c in "*?"):
        regex = glob_regex(pattern)
        return [f for f in repo_files if regex.fullmatch(f)]
    return [f for f in repo_files if f in (pattern, pattern + ".py")]


def used_files(body: dict, file_path: str, repo_files: list[str]) -> set[str]:
    """Return the tracked files one resource's JSON refers to, before imports."""
    found: set[str] = set()
    for value in strings(body):
        relative = repo_relative(value, file_path)
        if relative:
            found.update(matching_files(relative, repo_files))
    return found


def module_files(module: str, repo_files: set[str]) -> set[str]:
    """Return the ``src/`` files that loading ``module`` executes.

    ``a.b.c`` runs ``a/__init__.py``, ``a/b/__init__.py`` and either
    ``a/b/c.py`` or ``a/b/c/__init__.py``, whichever exist.
    """
    parts = module.split(".")
    candidates = [
        f"{SRC_ROOT}/{'/'.join(parts[:i])}/__init__.py" for i in range(1, len(parts))
    ]
    candidates += [
        f"{SRC_ROOT}/{'/'.join(parts)}.py",
        f"{SRC_ROOT}/{'/'.join(parts)}/__init__.py",
    ]
    return {c for c in candidates if c in repo_files}


def imported_modules(source: str) -> set[str]:
    """Return the absolute module names a Python source imports.

    ``from a import b`` yields both ``a`` and ``a.b`` because ``b`` may be a
    submodule. Relative imports are ignored (see the module docstring).
    """
    modules: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.add(node.module)
            modules.update(f"{node.module}.{alias.name}" for alias in node.names)
    return modules


def with_imports(
    files: set[str], repo_files: list[str], read_source: Callable[[str], str]
) -> set[str]:
    """Return ``files`` plus every ``src/`` module they import, transitively."""
    known = set(repo_files)
    closure = set(files)
    pending = [f for f in files if f.endswith(".py")]
    while pending:
        source = read_source(pending.pop())
        for module in imported_modules(source):
            for found in module_files(module, known) - closure:
                closure.add(found)
                pending.append(found)
    return closure


def references(body: dict) -> set[Resource]:
    """Return the resources a job points at through ``${resources...id}``."""
    return {
        (kind, key) for value in strings(body) for kind, key in REFERENCE.findall(value)
    }


def reach(start: Resource, all_resources: dict[Resource, dict]) -> set[Resource]:
    """Return ``start`` and every resource it runs, directly or through nested jobs."""
    seen: set[Resource] = set()
    pending = [start]
    while pending:
        ref = pending.pop()
        if ref in seen or ref not in all_resources:
            continue
        seen.add(ref)
        pending.extend(references(all_resources[ref]))
    return seen


def affected_resources(
    base: dict,
    head: dict,
    changed_files: set[str],
    repo_files: list[str],
    read_source: Callable[[str], str],
) -> tuple[set[Resource], set[str]]:
    """Apply steps 1 and 2: return affected resources and every file any resource uses."""
    file_path = head.get("workspace", {}).get("file_path", "")
    affected = changed_resources(base, head)
    every_used: set[str] = set()
    for ref, body in resources(head).items():
        closure = with_imports(
            used_files(body, file_path, repo_files), repo_files, read_source
        )
        every_used |= closure
        if closure & changed_files:
            affected.add(ref)
    return affected, every_used


def find_affected_units(
    base: dict,
    head: dict,
    changed_files: set[str],
    repo_files: list[str],
    read_source: Callable[[str], str],
) -> Result:
    """Run the whole algorithm (steps 1 to 4) and return the lookup result."""
    affected, every_used = affected_resources(
        base, head, changed_files, repo_files, read_source
    )
    all_resources = resources(head)
    result = Result(affected_resources=sorted(affected))
    for unit, auto_run in sorted(discover_units(head).items()):
        if reach(("jobs", f"{UNIT_PREFIX}{unit}"), all_resources) & affected:
            (result.units if auto_run else result.skipped_units).append(unit)
    result.unattributed = sorted(
        f for f in changed_files - every_used if f.startswith(UNATTRIBUTED_PREFIXES)
    )
    return result


def last_successful_sha(deployments: list[tuple[str, str]]) -> str | None:
    """Return the SHA of the first deployment in ``(sha, state)`` pairs whose state is success.

    Pairs are ordered newest first, as GitHub returns them. The deployment of
    the run asking is still ``in_progress``, so it is never chosen.
    """
    return next((sha for sha, state in deployments if state == "success"), None)


def run(*command: str, cwd: str | None = None) -> str:
    """Run a command and return its stdout; a non-zero exit raises."""
    return subprocess.run(
        command, cwd=cwd, check=True, capture_output=True, text=True, encoding="utf-8"
    ).stdout


def environment_deployments(environment: str) -> list[tuple[str, str]]:
    """Return ``(sha, latest status)`` for the environment's recent deployments, newest first."""
    listing = json.loads(
        run(
            "gh",
            "api",
            f"repos/{{owner}}/{{repo}}/deployments?environment={environment}&per_page=30",
        )
    )
    pairs = []
    for deployment in listing:
        statuses = json.loads(
            run(
                "gh",
                "api",
                f"repos/{{owner}}/{{repo}}/deployments/{deployment['id']}/statuses?per_page=1",
            )
        )
        pairs.append((deployment["sha"], statuses[0]["state"] if statuses else "none"))
    return pairs


def bundle_json(target: str, cwd: str | None, profile: str | None) -> dict:
    """Return ``databricks bundle validate -o json`` for a target, run in ``cwd``."""
    command = ["databricks", "bundle", "validate", "-t", target, "-o", "json"]
    if profile:
        command += ["--profile", profile]
    return json.loads(run(*command, cwd=cwd))


def bundle_json_at(sha: str, target: str, profile: str | None) -> dict:
    """Return the bundle JSON as it was at ``sha``, using a temporary git worktree."""
    with tempfile.TemporaryDirectory() as tmp:
        run("git", "worktree", "add", "--detach", tmp, sha)
        try:
            return bundle_json(target, tmp, profile)
        finally:
            run("git", "worktree", "remove", "--force", tmp)


def report(base_sha: str, result: Result) -> str:
    """Format the lookup result as Markdown for the step summary and the log."""
    lines = [f"## Affected units\n\nBase: `{base_sha}`\n"]
    lines.append(f"- Run: {', '.join(result.units) or 'none'}")
    lines.append(
        f"- Affected but opted out: {', '.join(result.skipped_units) or 'none'}"
    )
    affected = [f"{kind}.{key}" for kind, key in result.affected_resources]
    lines.append(f"- Affected resources: {', '.join(affected) or 'none'}")
    lines.append(
        f"- Unattributed changed files: {', '.join(result.unattributed) or 'none'}"
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    """Resolve base and head, run the lookup, print units, write the report."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--target", required=True, help="bundle target and GitHub environment"
    )
    parser.add_argument("--head", default="HEAD", help="must be the checked-out commit")
    parser.add_argument(
        "--base", help="default: last successful deployment of --target"
    )
    parser.add_argument("--profile", help="Databricks CLI profile for bundle validate")
    args = parser.parse_args()

    base_sha = args.base or last_successful_sha(environment_deployments(args.target))
    if not base_sha:
        print(
            f"no successful {args.target} deployment to compare against: running nothing"
        )
        return
    base_sha = run("git", "rev-parse", base_sha).strip()
    head_sha = run("git", "rev-parse", args.head).strip()
    changed = set(run("git", "diff", "--name-only", base_sha, head_sha).split())
    repo_files = run("git", "ls-files").split()
    result = find_affected_units(
        bundle_json_at(base_sha, args.target, args.profile),
        bundle_json(args.target, None, args.profile),
        changed,
        repo_files,
        lambda path: Path(path).read_text(encoding="utf-8"),
    )
    text = report(base_sha, result)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(text)
    print(text, file=sys.stderr)
    print("\n".join(result.units))


if __name__ == "__main__":
    main()
