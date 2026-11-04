"""Drop the given tables (explicit user approval needed for each list; log the output).

Usage: python drop_tables.py <catalog.schema.table> [...] --profile <PROFILE>
Runs on the first SQL warehouse; stop it afterwards.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "single-silver-landing-schema"))
from compare import cli, sql  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("tables", nargs="+")
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()
    warehouse = cli(args.profile, "warehouses", "list")[0]["id"]
    for table in args.tables:
        catalog, schema, name = table.split(".")
        sql(args.profile, warehouse, f"DROP TABLE `{catalog}`.`{schema}`.`{name}`")
        print(f"dropped {table}")


if __name__ == "__main__":
    main()
