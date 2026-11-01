# SCD2 selected over SCD1 per silver.md's precedence rule (SCD2 > SCD1 > SCD0).
# Reads only the rows Auto CDC changed in the bronze table (its change data
# feed) and applies them by key, so the run-time stamp lands only on changed
# rows (openspec refactor-airroi-clickstream-neon).
import sys

from pyspark import pipelines as dp

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.silver_landing import land_changes  # noqa: E402


@dp.temporary_view()
def products_changes():
    return land_changes(
        spark,
        "bronze_neon_publish.products_scd2",
        ["id"],
        "neon",
        scd2=True,
    )


dp.create_streaming_table(name="silver_landing.neon__products")
dp.create_auto_cdc_flow(
    target="silver_landing.neon__products",
    source="products_changes",
    keys=["id", "scd_valid_from_timestamp"],
    sequence_by="_commit_version",
    except_column_list=["_commit_version"],
    stored_as_scd_type=1,
)
