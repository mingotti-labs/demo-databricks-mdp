# Quarantine pattern: charities with no public ABN (~605 of ~66k, mostly
# Private Ancillary Funds -- confirmed via the CKAN SQL endpoint before this
# was written) have no stable identity for SCD tracking, so they're excluded
# from charity_register_scd1/scd2. Rather than silently dropping them inside
# the SCD modeling pipeline, they're kept here, visible and queryable --
# reading the same charity_register_raw with the complementary condition to
# the SCD pipeline's own filter, so every raw row lands somewhere.
from pyspark import pipelines as dp


@dp.materialized_view()
@dp.expect_or_drop("has_no_abn", "ABN IS NULL")
def charity_register_quarantine():
    return spark.read.table("charity_register_raw")
