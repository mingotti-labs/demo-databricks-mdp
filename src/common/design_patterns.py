"""Maps tables to the design pattern that builds them (register IDs)."""

import yaml

TAG = "design_pattern"
OBJECT_TYPES = {
    "STREAMING_TABLE": "STREAMING TABLE",
    "MATERIALIZED_VIEW": "MATERIALIZED VIEW",
    "MANAGED": "TABLE",
}
SHARED_SCHEMAS = {"silver_landing"}


def belongs_to(source, schema, table):
    """Whether `schema.table` is `source`'s: a shared schema prefixes each table `<source>__`."""
    return schema not in SHARED_SCHEMAS or table.startswith(f"{source}__")


def load_mapping(path):
    """Return the source -> {schemas, tables} mapping from `path`."""
    with open(path) as f:
        return yaml.safe_load(f)


def pattern_for(entry, schema, table):
    """Return the pattern ID of `schema.table`: its override, else the schema default."""
    return entry.get("tables", {}).get(f"{schema}.{table}", entry["schemas"][schema])
