"""Maps tables to the design pattern that builds them (register IDs)."""

import yaml

TAG = "design_pattern"
OBJECT_TYPES = {
    "STREAMING_TABLE": "STREAMING TABLE",
    "MATERIALIZED_VIEW": "MATERIALIZED VIEW",
    "MANAGED": "TABLE",
}


def load_mapping(path):
    """Return the source -> {schemas, tables} mapping from `path`."""
    with open(path) as f:
        return yaml.safe_load(f)


def pattern_for(entry, schema, table):
    """Return the pattern ID of `schema.table`: its override, else the schema default."""
    return entry.get("tables", {}).get(f"{schema}.{table}", entry["schemas"][schema])
