# Probe P1 (single-silver-landing-schema): one dataset with a qualified name,
# so the table stays put when the pipeline's default schema changes.
from pyspark import pipelines as dp


@dp.materialized_view(name="pattern_bronze.zz_p1_default_schema")
def zz_p1_default_schema():
    return spark.range(3)
