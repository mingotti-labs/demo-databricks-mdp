"""Run as the CI/CD service principal: create pipeline S, so S is owned and run by the SP."""

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.pipelines import NotebookLibrary, PipelineLibrary

w = WorkspaceClient()
print("running as", w.current_user.me().user_name)
created = w.pipelines.create(
    name="zz-probe-ownership-sp",
    catalog="mdp_dev",
    schema="bronze_yahoo",
    serverless=True,
    development=True,
    continuous=False,
    libraries=[
        PipelineLibrary(
            notebook=NotebookLibrary(
                path="/Workspace/Shared/poc/pipeline-ownership/zz_probe_pipeline.py"
            )
        )
    ],
)
print("pipeline", created.pipeline_id)
