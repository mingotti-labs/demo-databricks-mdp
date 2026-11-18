"""Probe P3 (pattern-scd2-history-migration): once-only backfill plus a live streaming
flow over the change feed of an append-only source without a timestamp.

Questions: does SQL stream the change feed (`WITH (readChangeFeed = true)`); can the
backfill and the live streaming flow share the target; does `_commit_timestamp` order the
live changes; does an appended row equal to the open version open no new version?

Reuses zz_p1_legacy; creates zz_p3_source (plain table, change feed on), the scratch
pipeline zz-probe-p3-stream-change-feed, zz_p3_migrated and its event log (4 slots).
Usage: uv run python p3.py --profile <PROFILE> --warehouse <WAREHOUSE_ID>
"""

import argparse
from pathlib import Path

from probe import SCHEMA, cli, create_pipeline, run_update, show, sql, upload

SOURCE = f"""
CREATE OR REPLACE TABLE {SCHEMA}.zz_p3_source
(asset_id STRING, asset_name STRING, asset_owner STRING)
TBLPROPERTIES (delta.enableChangeDataFeed = true)
"""
FIRST = f"INSERT INTO {SCHEMA}.zz_p3_source VALUES ('A1', 'Pump', 'Bob'), ('A3', 'Fan', 'Eve')"
SECOND = [
    f"INSERT INTO {SCHEMA}.zz_p3_source VALUES ('A1', 'Pump', 'Bob')",
    f"INSERT INTO {SCHEMA}.zz_p3_source VALUES ('A1', 'Pump', 'Fay'), ('A4', 'Drill', 'Gus')",
]
COMMITS = f"""
SELECT _commit_version, _commit_timestamp, asset_id, asset_owner
FROM table_changes('{SCHEMA}.zz_p3_source', 0) ORDER BY 1, 3
"""
MIGRATED = f"""
SELECT asset_id, asset_name, asset_owner, __START_AT, __END_AT
FROM {SCHEMA}.zz_p3_migrated ORDER BY asset_id, __START_AT
"""


def flows(pipeline_id: str) -> str:
    return f"""
SELECT origin.update_id, origin.flow_name, details:flow_progress.status AS status, timestamp
FROM event_log('{pipeline_id}')
WHERE event_type = 'flow_progress' AND details:flow_progress.status IS NOT NULL
ORDER BY timestamp
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--warehouse", required=True)
    a = parser.parse_args()
    p, w = a.profile, a.warehouse

    sql(p, w, SOURCE)
    sql(p, w, FIRST)
    user = cli(p, "current-user", "me")["userName"]
    remote = f"/Workspace/Users/{user}/poc/scd2-history-migration/p3_pipeline.sql"
    upload(p, str(Path(__file__).parent / "p3_pipeline.sql"), remote)
    pipeline_id = create_pipeline(p, "zz-probe-p3-stream-change-feed", [remote])
    print(f"--- pipeline {pipeline_id}")

    if run_update(p, pipeline_id) != "COMPLETED":
        return
    show(p, w, "after update 1 (expect legacy exact; A3 Di closed, Eve opened at commit 1; A1 Bob unchanged)", MIGRATED)

    for statement in SECOND:
        sql(p, w, statement)
    show(p, w, "source commits", COMMITS)
    run_update(p, pipeline_id)
    show(p, w, "after update 2 (expect no version for the repeated A1 Bob; A1 Fay and A4 at commit 3)", MIGRATED)

    run_update(p, pipeline_id)
    show(p, w, "after update 3, nothing appended (expect unchanged)", MIGRATED)
    show(p, w, "flow_progress events", flows(pipeline_id))


if __name__ == "__main__":
    main()
