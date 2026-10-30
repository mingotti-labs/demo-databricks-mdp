"""Compare old and new Silver Landing tables (single-silver-landing-schema).

For each `<source>.<entity>`: row counts of `silver_landing_<source>.<entity>`
and `silver_landing.<source>__<entity>`, and rows found in only one of them
(every column but `transformed_timestamp`, duplicates counted). Runs on the
first SQL warehouse; stop it afterwards.

Usage: python compare.py <catalog> <source>.<entity> [...] --profile <PROFILE>
"""

import argparse
import json
import subprocess


def cli(profile: str, *args: str) -> dict:
    out = subprocess.run(
        ["databricks", *args, "--profile", profile, "-o", "json"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return json.loads(out)


def sql(profile: str, warehouse: str, statement: str) -> list[list]:
    body = {"warehouse_id": warehouse, "statement": statement, "wait_timeout": "50s"}
    out = cli(profile, "api", "post", "/api/2.0/sql/statements", "--json", json.dumps(body))
    while out["status"]["state"] in ("PENDING", "RUNNING"):
        out = cli(profile, "api", "get", f"/api/2.0/sql/statements/{out['statement_id']}")
    if out["status"]["state"] != "SUCCEEDED":
        raise RuntimeError(out["status"])
    return out["result"].get("data_array") or []


def compare(catalog: str, source: str, entity: str) -> str:
    old = f"{catalog}.silver_landing_{source}.{entity}"
    new = f"{catalog}.silver_landing.{source}__{entity}"

    # Rows as JSON: set operations refuse MAP columns (airroi's metrics).
    row = "to_json(struct(* EXCEPT(transformed_timestamp)))"

    def only(a: str, b: str) -> str:
        return (
            f"(SELECT count(*) FROM (SELECT {row} FROM {a} "
            f"EXCEPT ALL SELECT {row} FROM {b}))"
        )

    return (
        f"SELECT '{source}.{entity}', (SELECT count(*) FROM {old}), "
        f"(SELECT count(*) FROM {new}), {only(old, new)}, {only(new, old)}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog")
    parser.add_argument("tables", nargs="+")
    parser.add_argument("--profile", required=True)
    args = parser.parse_args()
    warehouse = cli(args.profile, "warehouses", "list")[0]["id"]
    print("table | old | new | old_only | new_only")
    for name in args.tables:
        source, entity = name.split(".")
        for row in sql(args.profile, warehouse, compare(args.catalog, source, entity)):
            print(" | ".join(str(v) for v in row))


if __name__ == "__main__":
    main()
