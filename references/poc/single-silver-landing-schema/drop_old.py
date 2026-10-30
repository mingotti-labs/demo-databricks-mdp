"""Drop old Landing tables and their hidden twins in the given old schemas.

Only run once the new tables are verified and nothing reads the old ones (user
approval, 2026-10-30). Lists every table of each `silver_landing_<source>`
schema from system.information_schema and drops it.

Usage: python drop_old.py <catalog> <source> [...] --profile <PROFILE>
"""

import argparse

from compare import cli, sql


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog")
    parser.add_argument("sources", nargs="+")
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()
    warehouse = cli(args.profile, "warehouses", "list")[0]["id"]
    for source in args.sources:
        schema = f"silver_landing_{source}"
        rows = sql(
            args.profile,
            warehouse,
            "SELECT table_name FROM system.information_schema.tables "
            f"WHERE table_catalog = '{args.catalog}' AND table_schema = '{schema}'",
        )
        for (table,) in rows:
            sql(args.profile, warehouse, f"DROP TABLE `{args.catalog}`.`{schema}`.`{table}`")
            print(f"dropped {args.catalog}.{schema}.{table}")


if __name__ == "__main__":
    main()
