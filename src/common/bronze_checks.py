"""Bronze verification rules, driven by one spec file per source.

`verification/bronze_checks/<source>.yml` lists, per table, the raw table, its
key columns and its SCD tables. `verification/verify_bronze.py` gathers the
counts from Spark; the rules live here so they are tested without Spark.
"""

from pathlib import Path

import yaml

REQUIRED = {"raw", "scd2", "keys", "columns"}
OPTIONAL = {"scd1", "quarantine", "quarantine_not_empty", "absent_columns", "reference_rows"}
TOLERANCE = 0.02


def load_spec(path: str | Path) -> dict:
    spec = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    for key in ("source", "raw_schema", "publish_schema", "tables"):
        if key not in spec:
            raise ValueError(f"{path}: missing '{key}'")
    for table in spec["tables"]:
        missing = REQUIRED - table.keys()
        unknown = table.keys() - REQUIRED - OPTIONAL
        if missing or unknown:
            raise ValueError(f"{path}: {table.get('raw')}: missing {missing}, unknown {unknown}")
    return spec


def valid_distinct_keys_sql(table: str, keys: list[str]) -> str:
    """Count of distinct key combinations with no NULL key column."""
    not_null = " AND ".join(f"{k} IS NOT NULL" for k in keys)
    return (
        f"SELECT count(*) AS n FROM (SELECT DISTINCT {', '.join(keys)} "
        f"FROM {table} WHERE {not_null})"
    )


def check_table(table: dict, counts: dict, columns: set[str]) -> list[str]:
    """Failures for one table. `counts` holds raw, valid_distinct, scd2_current and,
    when the spec lists them, scd1_current and quarantine."""
    name, raw = table["raw"], counts["raw"]
    failures = []
    if raw == 0:
        failures.append(f"{name}: empty")
    if missing := set(table["columns"]) - columns:
        failures.append(f"{name}: missing columns {sorted(missing)}")
    if present := set(table.get("absent_columns", [])) & columns:
        failures.append(f"{name}: columns that should be gone {sorted(present)}")
    reference = table.get("reference_rows")
    if reference and abs(raw - reference) > reference * TOLERANCE:
        failures.append(f"{name}: {raw} rows, more than {TOLERANCE:.0%} from {reference}")
    valid = counts["valid_distinct"]
    if "quarantine" in table:
        if raw != valid + counts["quarantine"]:
            failures.append(
                f"{name}: raw {raw} != distinct valid keys {valid} + quarantine {counts['quarantine']}"
            )
        if table.get("quarantine_not_empty") and counts["quarantine"] == 0:
            failures.append(f"{name}: quarantine is unexpectedly empty")
    elif raw != valid:
        failures.append(f"{name}: {raw} rows but {valid} distinct non-null keys")
    for kind in ("scd2", "scd1"):
        if kind in table and counts[f"{kind}_current"] != valid:
            failures.append(f"{table[kind]}: {counts[f'{kind}_current']} current rows, expected {valid}")
    return failures
