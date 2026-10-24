"""P2: how many tables does the metastore hold, against the 500-table limit?"""

from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()

counts = spark.sql("""
    SELECT table_catalog, table_type, count(*) AS tables
    FROM system.information_schema.tables
    WHERE table_schema <> 'information_schema' AND table_catalog <> 'system'
    GROUP BY ALL
    ORDER BY ALL
""").collect()
for row in counts:
    print(row.table_catalog, row.table_type, row.tables)
print("total", sum(row.tables for row in counts))
