"""List hidden twins and event logs in mdp_dev and mdp_prd, and mark the orphans (read only).

A twin `__materialization_mat_<pipeline>_<table>_1` is an orphan when its pipeline no
longer exists or its visible table is gone from the same schema. An event log
`event_log_<pipeline>` is an orphan when its pipeline no longer exists. Runs on the
first SQL warehouse; stop it afterwards.

Usage: python find_orphans.py --profile <PROFILE>
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "single-silver-landing-schema"))
from compare import cli, sql  # noqa: E402

TWIN = re.compile(r"__materialization_mat_([0-9a-f_]{36})_(.+)_1")
EVENT_LOG = re.compile(r"event_log_([0-9a-f_]{36})")
CATALOGS = ("mdp_dev", "mdp_prd")


def tables(profile: str, warehouse: str) -> set[tuple[str, str, str]]:
    rows = []
    for catalog in CATALOGS:
        rows += sql(
            profile,
            warehouse,
            f"SELECT table_catalog, table_schema, table_name FROM {catalog}.information_schema.tables "
            "WHERE table_schema <> 'information_schema'",
        )
    return {tuple(r) for r in rows}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()

    warehouse = cli(args.profile, "warehouses", "list")[0]["id"]
    pipelines = {p["pipeline_id"].replace("-", "_") for p in cli(args.profile, "pipelines", "list-pipelines")}
    found = tables(args.profile, warehouse)
    for catalog, schema, name in sorted(found):
        if m := TWIN.fullmatch(name):
            pipeline, table = m.groups()
            gone = [w for w, bad in (("pipeline", pipeline not in pipelines),
                                     ("table", (catalog, schema, table) not in found)) if bad]
        elif m := EVENT_LOG.fullmatch(name):
            gone = ["pipeline"] if m.group(1) not in pipelines else []
        else:
            continue
        print(f"{'ORPHAN' if gone else 'live  '} {catalog}.{schema}.{name} {' '.join(gone)}")


if __name__ == "__main__":
    main()
