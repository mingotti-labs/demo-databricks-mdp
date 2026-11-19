"""Probe P4 (pattern-scd2-history-migration): a surrogate key `asset_sid` copied from the legacy
SCD2 table, a new key for new versions.

Variant A (`p4_pipeline_a.sql`): the live side reuses a legacy key when its row hash matches the
newest legacy row with that hash and that row is still open; otherwise `xxhash64(row_hash)`.
Variant B (`p4_pipeline_b.sql`): the live side also reads the target's own current rows.

Questions: does A keep the legacy keys and open no version for unchanged rows; what key does a
row get when it changes back to the open legacy state (A3 Hal -> Eli, A1 Ivy -> Cid); can a
pipeline view read its own target (B); does the fallback query (legacy key up to the cutover,
`xxhash64(row_hash, __START_AT)` after) give one key per version?

Legacy and live rows are inline in the pipeline file, so the only tables are the target and the
pipeline's event log (3 slots). Usage:
  uv run python p4.py --profile <PROFILE> --warehouse <ID> --variant a|b [--teardown]
"""

import argparse
from pathlib import Path

from probe import SCHEMA, cli, create_pipeline, run_update, show, sql, upload

UPDATES = [
    ("2026-01-01", "('A1', 'Pump', 'Cid'), ('A3', 'Fan', 'Hal'), ('A4', 'Belt', 'Gil')"),
    ("2026-02-01", "('A1', 'Pump', 'Ivy'), ('A3', 'Fan', 'Hal'), ('A5', 'Motor', 'Jo'), ('A6', 'Gear', NULL)"),
    ("2026-03-01", "('A1', 'Pump', 'Cid'), ('A3', 'Fan', 'Eli'), ('A5', 'Motor', 'Jo'), ('A6', 'Gear', NULL)"),
    ("2026-04-01", "('A1', 'Pump', 'Cid'), ('A3', 'Fan', 'Eli'), ('A5', 'Motor', 'Jo'), ('A6', 'Gear', NULL)"),
]
EXPECT = [
    "A1 Cid keeps 103 (no new version); A3 Hal opens a version with a new key; A4 Gil keeps 402",
    "A1 Ivy new key; A4 closed; A5 and A6 (NULL owner) new keys",
    "A1 back to Cid, A3 back to Eli: which key?",
    "same rows, new version: no change",
]
NAME = "zz-probe-p4-sid"
MIGRATED = f"""
SELECT asset_sid, asset_id, asset_owner, __START_AT, __END_AT
FROM {SCHEMA}.zz_p4_migrated ORDER BY asset_id, __START_AT
"""
CUTOVER = "TIMESTAMP'2025-05-01'"
FALLBACK = f"""
SELECT CASE WHEN __START_AT <= {CUTOVER} THEN asset_sid
            ELSE xxhash64(sha2(concat_ws('|', coalesce(asset_id, '<null>'), coalesce(asset_name, '<null>'),
                                         coalesce(asset_owner, '<null>')), 256), __START_AT) END AS asset_sid,
       asset_id, asset_owner, __START_AT, __END_AT
FROM {SCHEMA}.zz_p4_migrated ORDER BY asset_id, __START_AT
"""
DUPLICATE_KEYS = f"""
SELECT 'stored' AS key_source, asset_sid, count(*) FROM {SCHEMA}.zz_p4_migrated GROUP BY asset_sid HAVING count(*) > 1
UNION ALL
SELECT 'fallback', asset_sid, count(*) FROM ({FALLBACK}) GROUP BY asset_sid HAVING count(*) > 1
"""


def teardown(p: str, w: str) -> None:
    """Delete the probe pipeline, its target, the target's twin and the event log."""
    pipelines = cli(p, "pipelines", "list-pipelines", "--filter", f"name LIKE '{NAME}'")
    ids = [x["pipeline_id"] for x in pipelines]
    for pid in ids:
        cli(p, "pipelines", "delete", pid)
    sql(p, w, f"DROP TABLE IF EXISTS {SCHEMA}.zz_p4_migrated")
    owners = [pid.replace("-", "_") for pid in ids]
    catalog, schema = SCHEMA.split(".")
    for (name,) in sql(p, w, f"SELECT table_name FROM {catalog}.information_schema.tables WHERE table_schema = '{schema}'"):
        if any(name == f"event_log_{o}" or name.startswith(f"__materialization_mat_{o}_") for o in owners):
            sql(p, w, f"DROP TABLE IF EXISTS {SCHEMA}.`{name}`")
            print("--- dropped", name)
    show(p, w, f"left in {SCHEMA}", f"SELECT table_name FROM {catalog}.information_schema.tables WHERE table_schema = '{schema}'")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--warehouse", required=True)
    parser.add_argument("--variant", choices=["a", "b"])
    parser.add_argument("--teardown", action="store_true")
    a = parser.parse_args()
    p, w = a.profile, a.warehouse
    if a.teardown:
        teardown(p, w)
        return

    template = (Path(__file__).parent / f"p4_pipeline_{a.variant}.sql").read_text()
    local = Path(__file__).parent / "p4_rendered.sql"
    user = cli(p, "current-user", "me")["userName"]
    remote = f"/Workspace/Users/{user}/poc/scd2-history-migration/p4_pipeline.sql"
    existing = cli(p, "pipelines", "list-pipelines", "--filter", f"name LIKE '{NAME}'")
    pipeline_id = existing[0]["pipeline_id"] if existing else None

    for (version, rows), expect in zip(UPDATES, EXPECT):
        local.write_text(template.replace("__LIVE_ROWS__", rows).replace("__LIVE_VERSION__", version), newline="\n")
        upload(p, str(local), remote)
        if not pipeline_id:
            pipeline_id = create_pipeline(p, NAME, [remote])
            print(f"--- pipeline {pipeline_id}")
        print(f"--- live version {version}: {rows}")
        if run_update(p, pipeline_id) != "COMPLETED":
            break
        show(p, w, f"after {version} (expect {expect})", MIGRATED)
    local.unlink()

    show(p, w, "fallback query: legacy key up to the cutover, xxhash64(row_hash, __START_AT) after", FALLBACK)
    show(p, w, "keys used by more than one version", DUPLICATE_KEYS)


if __name__ == "__main__":
    main()
