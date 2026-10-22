"""SCD2 by MERGE: write only the rows whose business columns changed.

A changed key closes its current version and gets a new one, a new key gets a
version, a vanished key's current version is closed. Unchanged rows are not
touched. `transformed_timestamp` and the validity columns are stamped with
`current_timestamp()` only on the rows written; inserted versions carry the
source's `ingested_timestamp` unchanged.
"""

PLATFORM_COLUMNS = ("ingested_timestamp", "transformed_timestamp")
VALIDITY_COLUMNS = ("__START_AT", "__END_AT")


def business_columns(columns: list[str], keys: list[str]) -> list[str]:
    """Columns compared to detect a change: all but keys, platform and validity columns."""
    skip = set(keys) | set(PLATFORM_COLUMNS) | set(VALIDITY_COLUMNS)
    return [c for c in columns if c not in skip]


def _same(columns: list[str], left: str, right: str) -> str:
    return " AND ".join(f"{left}.`{c}` <=> {right}.`{c}`" for c in columns)


def merge_sql(target: str, source: str, keys: list[str], columns: list[str]) -> str:
    """The MERGE statement applying `source` (one row per key) to SCD2 `target`."""
    business = business_columns(columns, keys)
    data = keys + business
    merge_keys = ", ".join(f"s.`{k}` AS `_mk_{k}`" for k in keys)
    null_keys = ", ".join(f"NULL AS `_mk_{k}`" for k in keys)
    on_keys = " AND ".join(f"t.`{k}` <=> s.`{k}`" for k in keys)
    on_merge = " AND ".join(f"t.`{k}` <=> s.`_mk_{k}`" for k in keys)
    unchanged = _same(business, "t", "s")
    closed = "t.__END_AT = current_timestamp(), t.transformed_timestamp = current_timestamp()"
    insert_columns = ", ".join(f"`{c}`" for c in data)
    insert_values = ", ".join(f"s.`{c}`" for c in data)
    return f"""
MERGE INTO {target} AS t
USING (
  SELECT s.*, {merge_keys} FROM {source} AS s
  UNION ALL
  SELECT s.*, {null_keys}
  FROM {source} AS s JOIN {target} AS t ON {on_keys} AND t.__END_AT IS NULL
  WHERE NOT ({unchanged})
) AS s
ON {on_merge} AND t.__END_AT IS NULL
WHEN MATCHED AND NOT ({unchanged}) THEN UPDATE SET {closed}
WHEN NOT MATCHED THEN INSERT ({insert_columns}, ingested_timestamp, transformed_timestamp, __START_AT, __END_AT)
  VALUES ({insert_values}, s.ingested_timestamp, current_timestamp(), current_timestamp(), NULL)
WHEN NOT MATCHED BY SOURCE AND t.__END_AT IS NULL THEN UPDATE SET {closed}
"""
