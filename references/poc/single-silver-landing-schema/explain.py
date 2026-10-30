"""Explain differences between old and new Landing tables by a later fetch.

The old table stopped receiving changes when its definition left the code;
the new one received the run's fresh fetch. A row only in the old table is
explained when the new table has the same key in a later state (SCD2: the
version is now closed; SCD1: a newer `ingested_timestamp`). A row only in the
new table is explained when its key is new or is that later state. Prints the
unexplained counts, expected 0. Usage like compare.py.

Usage: python explain.py <catalog> <source>.<entity> [...] --profile <PROFILE>
"""

import argparse

from compare import cli, sql

TABLES = {
    "acnc.charity_register": (["ABN"], True),
    "geonames.cities": (["geonameid"], True),
    "sec.company_facts": (["cik", "taxonomy", "concept", "unit", "accn", "start", "end"], True),
    "sec.company_tickers": (["cik", "ticker"], True),
    "yahoo.prices": (["symbol", "date"], False),
    "yahoo.events": (["symbol", "date", "event_type"], False),
    "yahoo.options": (["symbol"], False),
    "yahoo.calendar": (["symbol"], True),
}


def statement(catalog: str, name: str, keys: list[str], scd2: bool) -> str:
    source, entity = name.split(".")
    old = f"{catalog}.silver_landing_{source}.{entity}"
    new = f"{catalog}.silver_landing.{source}__{entity}"
    if scd2:
        keys = keys + ["scd_valid_from_timestamp"]
        later = "n.scd_valid_to_timestamp IS NOT NULL AND o.scd_valid_to_timestamp IS NULL"
    else:
        later = "n.ingested_timestamp > o.ingested_timestamp"
    on = " AND ".join(f"o.`{k}` <=> n.`{k}`" for k in keys)
    return f"""
    WITH o_only AS (SELECT * EXCEPT(transformed_timestamp) FROM {old}
                    EXCEPT ALL SELECT * EXCEPT(transformed_timestamp) FROM {new}),
         n_only AS (SELECT * EXCEPT(transformed_timestamp) FROM {new}
                    EXCEPT ALL SELECT * EXCEPT(transformed_timestamp) FROM {old})
    SELECT '{name}',
      (SELECT count(*) FROM o_only o WHERE NOT EXISTS
         (SELECT 1 FROM {new} n WHERE {on} AND {later})),
      (SELECT count(*) FROM n_only n WHERE EXISTS
         (SELECT 1 FROM {old} o WHERE {on}) AND NOT EXISTS
         (SELECT 1 FROM {old} o WHERE {on} AND {later}))
    """


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog")
    parser.add_argument("tables", nargs="+")
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()
    warehouse = cli(args.profile, "warehouses", "list")[0]["id"]
    print("table | old_only_unexplained | new_only_unexplained")
    for name in args.tables:
        keys, scd2 = TABLES[name]
        for row in sql(args.profile, warehouse, statement(args.catalog, name, keys, scd2)):
            print(" | ".join(str(v) for v in row))


if __name__ == "__main__":
    main()
