# Generic Silver Normalised pipeline: executes the normalised spec named by
# the pipeline's `normalised_spec` configuration, one materialized view per
# base, bridge and extracted entity, plus value_lineage and any
# {entity}_quarantine. No per-source code; see docs/normalised-spec/README.md.
import sys
from functools import partial

from pyspark import pipelines as dp

workspace_file_path = spark.conf.get("workspace_file_path")
sys.path.insert(0, f"{workspace_file_path}/src")
from common import silver_normalised as sn  # noqa: E402
from common.normalised_spec import load_spec  # noqa: E402

spec = load_spec(f"{workspace_file_path}/{spark.conf.get('normalised_spec')}")


def define(name: str, build) -> None:
    """Register one materialized view whose query is `build()`."""
    dp.materialized_view(name=name)(lambda: build())


quarantined = {t["entity"] for t in spec.get("dependency_tolerance", [])}
for name in spec["base_entities"]:
    define(name, partial(sn.base, spark, spec, name))
    if name in quarantined:
        define(
            f"{name}_quarantine", partial(sn.base, spark, spec, name, quarantined=True)
        )
for name in spec.get("bridge_entities", {}):
    define(name, partial(sn.bridge, spark, spec, name))
for name in spec.get("extracted_entities", {}):
    define(name, partial(sn.extracted, spark, spec, name))
define("value_lineage", partial(sn.value_lineage, spark, spec))
