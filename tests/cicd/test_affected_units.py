"""Tests for cicd/affected_units.py, one group per scenario of the ci-affected-units spec.

The fixture is a miniature repo: two sources (acnc, airroi) that share
``src/common/shared.py`` through an intermediate module, a spec file named only
by pipeline configuration, and a source (ungm) with no run job.
"""

from affected_units import (
    discover_units,
    find_affected_units,
    imported_modules,
    last_successful_sha,
    matching_files,
    module_files,
    repo_relative,
    used_files,
)

WS = "/Workspace/me/.bundle/demo/dev/files"

SOURCES = {
    "src/layers/bronze/acnc/raw.py": "x = 1",
    "src/layers/bronze/ungm/raw.py": "x = 1",
    "src/layers/silver/normalised/pipeline.py": "from layers.silver.normalised import transforms",
    "src/layers/silver/normalised/transforms.py": "from common import shared",
    "src/layers/silver/normalised/specs/acnc.yml": "a: 1",
    "src/layers/silver/normalised/specs/airroi.yml": "a: 1",
    "src/common/shared.py": "y = 1",
    "src/common/__init__.py": "",
    "src/layers/__init__.py": "",
    "README.md": "",
    "openspec/changes/x/design.md": "",
}
REPO_FILES = list(SOURCES)


def read_source(path):
    return SOURCES[path]


def pipeline(libraries, configuration=None):
    return {"libraries": libraries, "configuration": configuration or {}}


def bundle(*, acnc_row_limit="500", run_airroi_tags=None, with_run_jobs=True):
    jobs = {
        "silver_acnc": {
            "tasks": [
                {
                    "pipeline_task": {
                        "pipeline_id": "${resources.pipelines.silver_normalised_acnc.id}"
                    }
                }
            ]
        },
        "silver_airroi": {
            "tasks": [
                {
                    "pipeline_task": {
                        "pipeline_id": "${resources.pipelines.silver_normalised_airroi.id}"
                    }
                }
            ]
        },
    }
    if with_run_jobs:
        jobs["run_acnc"] = {
            "tasks": [
                {
                    "pipeline_task": {
                        "pipeline_id": "${resources.pipelines.acnc_ingestion.id}"
                    }
                },
                {"run_job_task": {"job_id": "${resources.jobs.silver_acnc.id}"}},
            ]
        }
        jobs["run_airroi"] = {
            "tags": run_airroi_tags or {"ci_auto_run": "false"},
            "tasks": [
                {"run_job_task": {"job_id": "${resources.jobs.silver_airroi.id}"}}
            ],
        }
    return {
        "workspace": {"file_path": WS},
        "resources": {
            "pipelines": {
                "acnc_ingestion": pipeline(
                    [{"glob": {"include": f"{WS}/src/layers/bronze/acnc/**"}}],
                    {"acnc_row_limit": acnc_row_limit},
                ),
                "ungm_ingestion": pipeline(
                    [{"glob": {"include": f"{WS}/src/layers/bronze/ungm/**"}}]
                ),
                "silver_normalised_acnc": pipeline(
                    [
                        {
                            "file": {
                                "path": f"{WS}/src/layers/silver/normalised/pipeline.py"
                            }
                        }
                    ],
                    {"normalised_spec": "src/layers/silver/normalised/specs/acnc.yml"},
                ),
                "silver_normalised_airroi": pipeline(
                    [
                        {
                            "file": {
                                "path": f"{WS}/src/layers/silver/normalised/pipeline.py"
                            }
                        }
                    ],
                    {
                        "normalised_spec": "src/layers/silver/normalised/specs/airroi.yml"
                    },
                ),
            },
            "jobs": jobs,
        },
    }


def lookup(changed, base=None, head=None):
    return find_affected_units(
        base or bundle(), head or bundle(), set(changed), REPO_FILES, read_source
    )


class TestUnitDiscovery:
    def test_run_jobs_are_units_others_are_not(self):
        assert discover_units(bundle()) == {"acnc": True, "airroi": False}

    def test_opt_out_tag_only_when_false(self):
        assert (
            discover_units(bundle(run_airroi_tags={"ci_auto_run": "true"}))["airroi"]
            is True
        )


class TestOptOut:
    def test_paid_source_changed_runs_nothing_and_is_reported_skipped(self):
        result = lookup(["src/layers/silver/normalised/specs/airroi.yml"])
        assert result.units == []
        assert result.skipped_units == ["airroi"]


class TestConfigChanges:
    def test_variable_change_affects_the_resource_and_its_unit(self):
        result = lookup([], head=bundle(acnc_row_limit="10"))
        assert ("pipelines", "acnc_ingestion") in result.affected_resources
        assert result.units == ["acnc"]

    def test_new_resource_is_affected(self):
        result = lookup([], base=bundle(with_run_jobs=False))
        assert ("jobs", "run_acnc") in result.affected_resources
        assert result.units == ["acnc"]

    def test_identical_bundles_and_no_files_run_nothing(self):
        assert lookup([]).units == []


class TestFileChanges:
    def test_pipeline_source_file_affects_its_pipeline(self):
        result = lookup(["src/layers/bronze/acnc/raw.py"])
        assert result.affected_resources == [("pipelines", "acnc_ingestion")]
        assert result.units == ["acnc"]

    def test_shared_module_affects_through_an_intermediate_import(self):
        result = lookup(["src/common/shared.py"])
        assert ("pipelines", "silver_normalised_acnc") in result.affected_resources
        assert ("pipelines", "silver_normalised_airroi") in result.affected_resources
        assert result.units == ["acnc"]
        assert result.skipped_units == ["airroi"]

    def test_spec_file_named_only_by_configuration(self):
        result = lookup(["src/layers/silver/normalised/specs/acnc.yml"])
        assert result.affected_resources == [("pipelines", "silver_normalised_acnc")]
        assert result.units == ["acnc"]

    def test_reached_through_a_nested_job(self):
        result = lookup(["src/layers/silver/normalised/pipeline.py"])
        assert result.units == ["acnc"]


class TestUnmatchedChangesRunNothing:
    def test_docs_only(self):
        result = lookup(["README.md", "openspec/changes/x/design.md"])
        assert result.units == []
        assert result.unattributed == []

    def test_source_without_a_run_job_runs_nothing(self):
        result = lookup(["src/layers/bronze/ungm/raw.py"])
        assert result.units == []
        assert result.affected_resources == [("pipelines", "ungm_ingestion")]

    def test_unused_src_file_is_listed_as_unattributed(self):
        sources = {**SOURCES, "src/orphan.py": ""}
        result = find_affected_units(
            bundle(), bundle(), {"src/orphan.py"}, list(sources), lambda p: sources[p]
        )
        assert result.units == []
        assert result.unattributed == ["src/orphan.py"]


class TestHelpers:
    def test_imported_modules_covers_import_forms_and_ignores_relative(self):
        source = "import a.b\nfrom c import d\nfrom e.f import g\nfrom . import h\n"
        assert imported_modules(source) == {"a.b", "c", "c.d", "e.f", "e.f.g"}

    def test_module_files_includes_parent_packages(self):
        files = {"src/common/__init__.py", "src/common/shared.py"}
        assert module_files("common.shared", files) == files

    def test_module_files_ignores_third_party(self):
        assert module_files("pyspark.sql", {"src/common/shared.py"}) == set()

    def test_repo_relative_strips_workspace_prefix_only(self):
        assert repo_relative(f"{WS}/src/a.py", WS) == "src/a.py"
        assert repo_relative("src/a.py", WS) == "src/a.py"
        assert repo_relative("/Volumes/x/y", WS) is None
        assert repo_relative("${var.catalog}", WS) is None

    def test_notebook_path_without_suffix_matches_py_file(self):
        assert matching_files("src/common/shared", REPO_FILES) == [
            "src/common/shared.py"
        ]

    def test_glob_double_star_crosses_folders_single_star_does_not(self):
        assert "src/layers/bronze/acnc/raw.py" in matching_files(
            "src/layers/bronze/**", REPO_FILES
        )
        assert matching_files("src/layers/*", REPO_FILES) == ["src/layers/__init__.py"]


    def test_data_glob_in_a_job_parameter_names_the_data_files(self):
        body = {"base_parameters": {"source_glob": f"{WS}/data/portfolio/*.csv"}}
        repo = ["data/portfolio/settings.csv", "data/portfolio/README.md", "src/a.py"]
        assert used_files(body, WS, repo) == {"data/portfolio/settings.csv"}


class TestBaseDeployment:
    def test_first_success_skipping_the_running_deployment(self):
        pairs = [("c3", "in_progress"), ("c2", "failure"), ("c1", "success")]
        assert last_successful_sha(pairs) == "c1"

    def test_no_success_returns_none(self):
        assert last_successful_sha([("c1", "failure")]) is None
