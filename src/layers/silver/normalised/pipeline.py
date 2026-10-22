# Generic Silver Normalised pipeline: executes the normalised spec named by
# the pipeline's `normalised_spec` configuration, one materialized view per
# base, bridge and extracted entity, plus value_lineage and any
# {entity}_quarantine. No per-source code; see references/docs/normalised-spec/README.md.
# Sources moved to correct-platform-timestamps (acnc) use rebuild.py instead.
import sys

from pyspark import pipelines as dp

workspace_file_path = spark.conf.get("workspace_file_path")
sys.path.insert(0, f"{workspace_file_path}/src")
from common.normalised_spec import load_spec  # noqa: E402
from layers.silver.normalised import transforms as sn  # noqa: E402

spec = load_spec(f"{workspace_file_path}/{spark.conf.get('normalised_spec')}")


def define(name: str, build) -> None:
    """Register one materialized view whose query is `build()`."""
    dp.materialized_view(name=name)(lambda: build())


for name, build in sn.builders(spark, spec).items():
    define(name, build)
