"""Count tables per catalog and schema in mdp_dev and mdp_prd, hidden twins included (read only).

Usage: python count_by_schema.py --profile <PROFILE>
"""

import argparse
from collections import Counter

from find_orphans import cli, tables


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()
    warehouse = cli(args.profile, "warehouses", "list")[0]["id"]
    counts = Counter((c, s) for c, s, _ in tables(args.profile, warehouse))
    for (catalog, schema), n in sorted(counts.items()):
        print(f"{n:4} {catalog}.{schema}")
    for catalog in sorted({c for c, _ in counts}):
        print(f"{sum(n for (c, _), n in counts.items() if c == catalog):4} {catalog} total")


if __name__ == "__main__":
    main()
