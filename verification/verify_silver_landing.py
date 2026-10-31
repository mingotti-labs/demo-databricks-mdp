# Databricks notebook source
# Checks every Silver Landing table against its selected Bronze Publish
# source: row count parity, non-null source_name/transformed_timestamp,
# and (for SCD2-sourced entities) is_current correctly derived from
# scd_valid_to_timestamp. See references/docs/medallion/silver.md and
# openspec/changes/phase4a-silver-landing/design.md for the full contract.
import sys

dbutils.widgets.text("catalog", "")
dbutils.widgets.text("source", "")
dbutils.widgets.text("workspace_file_path", "")
catalog = dbutils.widgets.get("catalog")
source = dbutils.widgets.get("source")
workspace_file_path = dbutils.widgets.get("workspace_file_path")

sys.path.insert(0, f"{workspace_file_path}/src")
from common import silver_landing_checks  # noqa: E402

# One file per source in verification/silver_landing_checks/; an empty source
# checks every file. A source whose Bronze Publish carries ingested_timestamp
# (stamped at its own _raw layer) has it propagated unchanged by Silver Landing,
# never stamped or overwritten.
ENTITIES = silver_landing_checks.load_entities(
    f"{workspace_file_path}/verification/silver_landing_checks", source
)


def count(fqn: str, where: str = "1=1") -> int:
    return spark.sql(f"SELECT count(*) AS n FROM {fqn} WHERE {where}").collect()[0]["n"]


failures = []

for entity in ENTITIES:
    silver_fqn = f"{catalog}.silver_landing.{entity['source']}__{entity['table']}"
    bronze_fqn = f"{catalog}.{entity['bronze_schema']}.{entity['bronze_table']}"
    label = f"{entity['source']}.{entity['table']}"

    silver_count = count(silver_fqn)
    bronze_count = count(bronze_fqn)
    if silver_count != bronze_count:
        failures.append(
            f"{label}: row count mismatch (silver={silver_count} bronze={bronze_count})"
        )

    bad_provenance = count(
        silver_fqn, "source_name IS NULL OR transformed_timestamp IS NULL"
    )
    if bad_provenance:
        failures.append(
            f"{label}: {bad_provenance} rows with null source_name/transformed_timestamp"
        )

    if entity["scd2"]:
        bad_is_current = count(
            silver_fqn,
            "is_current != (scd_valid_to_timestamp IS NULL)",
        )
        if bad_is_current:
            failures.append(
                f"{label}: {bad_is_current} rows with is_current not matching scd_valid_to_timestamp"
            )

    if entity["ingested_timestamp"]:
        # Current rows only: an SCD2 version closed before a source's
        # ingested_timestamp retrofit keeps the column null (acnc has 10
        # such rows in dev; see phase4e's design.md) -- downstream `max()`
        # aggregation already ignores them, so verification need not treat
        # pre-retrofit history as broken. Every source here is SCD2.
        current_clause = "is_current AND " if entity["scd2"] else ""
        null_ingested = count(silver_fqn, f"{current_clause}ingested_timestamp IS NULL")
        if null_ingested:
            failures.append(
                f"{label}: {null_ingested} current rows with null ingested_timestamp "
                f"(expected non-null for {entity['source']})"
            )

assert not failures, "Silver Landing verification failed:\n" + "\n".join(failures)

dbutils.notebook.exit(f"Silver Landing OK -- {len(ENTITIES)} entities verified")
