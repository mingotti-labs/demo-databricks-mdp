# Databricks notebook source
# Standard profiling job for Silver Normalised design time. Profiles one
# source's Silver Landing tables (all SCD2 versions, since Landing keeps
# every version) and returns the evidence as one JSON document via
# dbutils.notebook.exit -- nothing is written to any table or volume. The
# output field names are the contract docs/templates/silver-normalised-*.md
# refer to. Pass 1 (no dependency_pairs): column stats + value overlaps.
# Pass 2 (dependency_pairs set): violating determinant values per pair.
import json

dbutils.widgets.text("catalog", "")
dbutils.widgets.text("source", "")
dbutils.widgets.text("dependency_pairs", "")
dbutils.widgets.text("overlap_max_distinct", "1000")

catalog = dbutils.widgets.get("catalog")
source = dbutils.widgets.get("source")
dependency_pairs = dbutils.widgets.get("dependency_pairs").strip()
overlap_max_distinct = int(dbutils.widgets.get("overlap_max_distinct"))
schema = f"silver_landing_{source}"

TOP_N = 20
DELIMITERS = [";", ",", "|"]
COMPLEX_TYPES = {"STRUCT", "ARRAY", "MAP", "VARIANT"}

# COMMAND ----------


def q(name: str) -> str:
    """Backtick-quote one identifier part."""
    return "`" + name.replace("`", "``") + "`"


def fqn(table: str) -> str:
    """Fully qualified, quoted name of a Landing table."""
    return f"{q(catalog)}.{q(schema)}.{q(table)}"


def landing_columns() -> dict[str, list[dict]]:
    """Columns of every table in the source's Landing schema, in order."""
    rows = spark.sql(
        f"""
        SELECT table_name, column_name, data_type
        FROM {q(catalog)}.information_schema.columns
        WHERE table_schema = '{schema}'
        ORDER BY table_name, ordinal_position
        """
    ).collect()
    tables: dict[str, list[dict]] = {}
    for r in rows:
        tables.setdefault(r.table_name, []).append(
            {"name": r.column_name, "type": r.data_type}
        )
    return tables


# COMMAND ----------


def column_stats(table: str, columns: list[dict]) -> tuple[int, list[dict]]:
    """Row count and per-column stats for one table, in one aggregate query."""
    exprs = ["count(*) AS row_count"]
    for i, c in enumerate(columns):
        col = q(c["name"])
        exprs.append(f"count({col}) AS nn_{i}")
        if c["type"] in COMPLEX_TYPES:
            continue
        exprs.append(f"count(DISTINCT {col}) AS nd_{i}")
        exprs.append(f"max(length(CAST({col} AS STRING))) AS ml_{i}")
        for j, d in enumerate(DELIMITERS):
            exprs.append(f"count_if(CAST({col} AS STRING) LIKE '%{d}%') AS dl_{i}_{j}")
    agg = (
        spark.sql(f"SELECT {', '.join(exprs)} FROM {fqn(table)}").collect()[0].asDict()
    )

    row_count = agg["row_count"]
    stats = []
    for i, c in enumerate(columns):
        nulls = row_count - agg[f"nn_{i}"]
        s = {
            "column": c["name"],
            "type": c["type"],
            "null_pct": round(100 * nulls / row_count, 2) if row_count else None,
        }
        if c["type"] not in COMPLEX_TYPES:
            s["distinct_count"] = agg[f"nd_{i}"]
            s["max_length"] = agg[f"ml_{i}"]
            s["delimiter_rows"] = {
                d: agg[f"dl_{i}_{j}"] for j, d in enumerate(DELIMITERS)
            }
            s["top_values"] = top_values(table, c["name"])
        stats.append(s)
    return row_count, stats


def top_values(table: str, column: str) -> list[dict]:
    """Most frequent non-null values of one column, as strings."""
    rows = spark.sql(
        f"""
        SELECT CAST({q(column)} AS STRING) AS value, count(*) AS rows
        FROM {fqn(table)}
        WHERE {q(column)} IS NOT NULL
        GROUP BY 1
        ORDER BY rows DESC, value
        LIMIT {TOP_N}
        """
    ).collect()
    return [{"value": r.value, "rows": r.rows} for r in rows]


# COMMAND ----------


def value_overlaps(stats: dict[str, list[dict]]) -> list[dict]:
    """Shared distinct values between every pair of low-cardinality string columns."""
    candidates = [
        (t, s["column"])
        for t, cols in stats.items()
        for s in cols
        if s["type"] == "STRING" and 0 < s["distinct_count"] <= overlap_max_distinct
    ]
    if len(candidates) < 2:
        return []
    selects = [
        f"SELECT DISTINCT '{t}' AS tbl, '{c}' AS col, {q(c)} AS value FROM {fqn(t)} WHERE {q(c)} IS NOT NULL"
        for t, c in candidates
    ]
    spark.sql(" UNION ALL ".join(selects)).createOrReplaceTempView("profile_values")
    rows = spark.sql(
        """
        SELECT a.tbl AS table_a, a.col AS column_a, b.tbl AS table_b, b.col AS column_b,
               count(*) AS shared_values
        FROM profile_values a
        JOIN profile_values b
          ON a.value = b.value AND (a.tbl, a.col) < (b.tbl, b.col)
        GROUP BY ALL
        ORDER BY shared_values DESC, table_a, column_a, table_b, column_b
        """
    ).collect()
    return [r.asDict() for r in rows]


# COMMAND ----------


def dependency_checks(pairs: list[dict]) -> list[dict]:
    """Violating determinant values per pair (N4's zero-exception check)."""
    results = []
    for p in pairs:
        violating = spark.sql(
            f"""
            SELECT count(*) AS n FROM (
              SELECT {q(p["determinant"])}
              FROM {fqn(p["table"])}
              WHERE {q(p["determinant"])} IS NOT NULL
              GROUP BY 1
              HAVING count(DISTINCT {q(p["dependent"])}) > 1
            )
            """
        ).collect()[0]["n"]
        results.append({**p, "violating_values": violating})
    return results


# COMMAND ----------

if dependency_pairs:
    profile = {
        "source": source,
        "pass": 2,
        "dependency_checks": dependency_checks(json.loads(dependency_pairs)),
    }
else:
    tables = landing_columns()
    if not tables:
        raise ValueError(f"No tables found in {catalog}.{schema}")
    row_counts, stats = {}, {}
    for table, columns in tables.items():
        row_counts[table], stats[table] = column_stats(table, columns)
    profile = {
        "source": source,
        "pass": 1,
        "overlap_max_distinct": overlap_max_distinct,
        "tables": [
            {"table": t, "row_count": row_counts[t], "columns": stats[t]}
            for t in tables
        ],
        "value_overlaps": value_overlaps(stats),
    }

dbutils.notebook.exit(json.dumps(profile, default=str))
