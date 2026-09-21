# Full-refresh batch pull of UNGM's UNSPSC classification data -- the
# source API has no pagination and no incremental cursor/updated-at field
# (confirmed via a real request against both the test and production
# endpoints before this was written: one call returns the complete current
# tree, ~13,335 records / ~1.4MB in production), so a Materialized View
# that re-fetches everything each run is the correct dataset type, not a
# Streaming Table artificially wrapped around a non-streaming source.
import sys

from pyspark import pipelines as dp

# src/common isn't on the path by default -- glob-including it in this
# pipeline's `libraries` doesn't add it to sys.path (confirmed via a real
# ModuleNotFoundError). ${workspace.file_path} is the same DAB-native
# variable the documented `--editable ${workspace.file_path}` shared-package
# pattern relies on; used directly here instead, since that pattern needs
# proper setuptools/pyproject.toml package-discovery config this repo
# doesn't have yet.
sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.ungm import fetch_ungm_endpoint  # noqa: E402

BASE_URL = spark.conf.get("ungm_base_url")


@dp.materialized_view()
def unspsc_public_raw():
    records = fetch_ungm_endpoint(BASE_URL, "/API/UNSPSCs")
    return spark.createDataFrame(records)
