# Quarantine pattern: ~10 of 6,260 subdivision_codes_raw rows are genuine
# full-row duplicates on the SCD key (subdivision_code, language_code,
# subdivision_name) -- confirmed via a real pipeline run
# (DUPLICATE_KEY_VIOLATION), not assumed from the source's column names.
# Every duplicate group has byte-identical values in every other column
# too (verified before this was written), so no information is lost by
# keeping one copy per key -- but rather than silently dropping the extra
# copies inside subdivision_codes_deduped, they're kept here, visible and
# queryable, same reasoning as ACNC's charity_register_quarantine. Reads
# the same subdivision_codes_raw with the complementary condition to
# subdivision_codes_deduped's dropDuplicates(), so every raw row lands
# somewhere: `raw = deduped + quarantine` exactly.
from pyspark import pipelines as dp
from pyspark.sql import Window
from pyspark.sql.functions import monotonically_increasing_id, row_number

KEY_COLUMNS = ["subdivision_code", "language_code", "subdivision_name"]


@dp.materialized_view()
def subdivision_codes_quarantine():
    df = spark.read.table("bronze_iso.subdivision_codes_raw")
    ranked = df.withColumn(
        "_dup_rank",
        row_number().over(Window.partitionBy(*KEY_COLUMNS).orderBy(monotonically_increasing_id())),
    )
    return ranked.filter("_dup_rank > 1").drop("_dup_rank")
