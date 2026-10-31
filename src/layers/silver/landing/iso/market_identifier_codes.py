# Reads only the rows Auto CDC inserted or closed in the SCD2 table (its change
# data feed) and applies them by version key (openspec rollout-bronze-full-pattern).
# Bronze keeps the file's dates as text (`20260928`); Landing turns the four date
# columns into dates, null where the source is empty. A value that does not read
# as a date fails the update (ANSI) instead of becoming null.
import sys

from pyspark import pipelines as dp
from pyspark.sql import functions as F

sys.path.insert(0, f"{spark.conf.get('workspace_file_path')}/src")
from common.silver_landing import land_changes  # noqa: E402

KEYS = ["market_identifier_code"]
DATE_COLUMNS = ["creation_date", "last_update_date", "last_validation_date", "expiry_date"]
DATE_FORMAT = "yyyyMMdd"


@dp.temporary_view()
def market_identifier_codes_changes():
    changes = land_changes(
        spark, "bronze_iso_publish.market_identifier_codes_scd2", KEYS, "iso"
    )
    for column in DATE_COLUMNS:
        changes = changes.withColumn(
            column,
            F.when(F.col(column) != "", F.to_date(F.col(column), DATE_FORMAT)),
        )
    return changes


dp.create_streaming_table(name="silver_landing.iso__market_identifier_codes")
dp.create_auto_cdc_flow(
    target="silver_landing.iso__market_identifier_codes",
    source="market_identifier_codes_changes",
    keys=[*KEYS, "scd_valid_from_timestamp"],
    sequence_by="_commit_version",
    except_column_list=["_commit_version"],
    stored_as_scd_type=1,
)
