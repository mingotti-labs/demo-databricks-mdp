"""Silver Landing check lists, one spec file per source.

`verification/silver_landing_checks/<source>.yml` lists the Landing tables of a
source, each with the Bronze Publish table it is built from.
`verification/verify_silver_landing.py` runs the checks; reading the files is
here so it is tested without Spark.
"""

from pathlib import Path

import yaml

SPEC_KEYS = {"source", "ingested_timestamp", "tables"}
TABLE_KEYS = {"table", "bronze_schema", "bronze_table", "scd2"}


def load_spec(path: str | Path) -> dict:
    """One source's file; fails on a missing or unknown key, or a source that is not the file name."""
    path = Path(path)
    spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    if set(spec) != SPEC_KEYS:
        raise ValueError(
            f"{path}: keys must be {sorted(SPEC_KEYS)}, got {sorted(spec)}"
        )
    if spec["source"] != path.stem:
        raise ValueError(f"{path}: source {spec['source']!r} is not the file name")
    for table in spec["tables"]:
        if set(table) != TABLE_KEYS:
            raise ValueError(
                f"{path}: {table.get('table')}: keys must be {sorted(TABLE_KEYS)}"
            )
    return spec


def load_entities(directory: str | Path, source: str = "") -> list[dict]:
    """The Landing tables to check: those of `source`, or of every source when empty.

    Each entity is a table's entry plus its source and whether that source's
    Bronze Publish carries `ingested_timestamp`.
    """
    directory = Path(directory)
    if source:
        path = directory / f"{source}.yml"
        if not path.exists():
            raise ValueError(f"no Silver Landing checks for source {source!r}")
        paths = [path]
    else:
        paths = sorted(directory.glob("*.yml"))
    entities = []
    for path in paths:
        spec = load_spec(path)
        for table in spec["tables"]:
            entities.append(
                {
                    "source": spec["source"],
                    "ingested_timestamp": spec["ingested_timestamp"],
                }
                | table
            )
    return entities
