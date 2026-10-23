# SCD2 selected over SCD1 per silver.md's precedence rule (SCD2 > SCD1 > SCD0).
# Reads only the rows Auto CDC inserted or closed in the bronze SCD2 table (its
# change data feed) and applies them by version key, so land()'s run-time stamp
# lands only on changed rows. The SCD2 table has no platform timestamps: the
# version's fetch time, __START_AT, becomes ingested_timestamp here (openspec
# correct-platform-timestamps, probes P4 and P7).
import sys

from pyspark import pipelines as dp
from pyspark.sql import functions as F

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.silver_landing import land  # noqa: E402


@dp.temporary_view()
def charity_register_changes():
    df = (
        spark.readStream.option("readChangeFeed", "true")
        .table("bronze_acnc_publish.charity_register_scd2")
        .where("_change_type IN ('insert', 'update_postimage')")
        .drop("_change_type", "_commit_timestamp")
    )
    df = df.withColumn("ingested_timestamp", F.col("__START_AT"))
    return land(df, natural_keys=["ABN"], source_name="acnc", scd2=True)


dp.create_streaming_table(name="silver_landing_acnc.charity_register")
dp.create_auto_cdc_flow(
    target="silver_landing_acnc.charity_register",
    source="charity_register_changes",
    keys=["ABN", "scd_valid_from_timestamp"],
    sequence_by="_commit_version",
    except_column_list=["_commit_version"],
    stored_as_scd_type=1,
)
