"""Probe P2 (pattern-scd2-history-migration): snapshot flow WITH VERSION over a
materialized view without a timestamp, next to the once-only backfill (P1b).

Questions: does information_schema last_altered move on a refresh and work as the
version; can the snapshot flow share the target with the backfill; does the first
update give the legacy history plus only the real differences; does a run without a
refresh process nothing?

Reuses zz_p1_legacy; creates zz_p2_base (plain table), the materialized view
zz_p2_source (created on the SQL warehouse), the scratch pipeline
zz-probe-p2-snapshot-version, zz_p2_migrated and its event log (about 6 slots).
Usage: uv run python p2.py --profile <PROFILE> --warehouse <WAREHOUSE_ID>
"""

import argparse
from pathlib import Path

from probe import SCHEMA, cli, create_pipeline, run_update, show, sql, upload

BASE = f"""
CREATE OR REPLACE TABLE {SCHEMA}.zz_p2_base AS
SELECT * FROM VALUES
  ('A1', 'Pump', 'Bob'),
  ('A3', 'Fan',  'Eve')
  AS t(asset_id, asset_name, asset_owner)
"""
SOURCE = f"""
CREATE OR REPLACE MATERIALIZED VIEW {SCHEMA}.zz_p2_source AS
SELECT asset_id, asset_name, asset_owner FROM {SCHEMA}.zz_p2_base
"""
CHANGES = [
    f"UPDATE {SCHEMA}.zz_p2_base SET asset_owner = 'Fay' WHERE asset_id = 'A1'",
    f"DELETE FROM {SCHEMA}.zz_p2_base WHERE asset_id = 'A3'",
    f"INSERT INTO {SCHEMA}.zz_p2_base VALUES ('A4', 'Drill', 'Gus')",
]
LAST_ALTERED = f"""
SELECT table_name, table_type, last_altered FROM mdp_dev.information_schema.tables
WHERE table_schema = 'pattern_bronze_publish' AND table_name = 'zz_p2_source'
"""
MIGRATED = f"""
SELECT asset_id, asset_name, asset_owner, __START_AT, __END_AT
FROM {SCHEMA}.zz_p2_migrated ORDER BY asset_id, __START_AT
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

    sql(p, w, BASE)
    sql(p, w, SOURCE)
    show(p, w, "view created", LAST_ALTERED)

    user = cli(p, "current-user", "me")["userName"]
    remote = f"/Workspace/Users/{user}/poc/scd2-history-migration/p2_pipeline.sql"
    upload(p, str(Path(__file__).parent / "p2_pipeline.sql"), remote)
    pipeline_id = create_pipeline(p, "zz-probe-p2-snapshot-version", [remote])
    print(f"--- pipeline {pipeline_id}")

    if run_update(p, pipeline_id) != "COMPLETED":
        return
    show(p, w, "after update 1 (expect legacy history + A3 Eve from the view)", MIGRATED)

    for statement in CHANGES:
        sql(p, w, statement)
    sql(p, w, f"REFRESH MATERIALIZED VIEW {SCHEMA}.zz_p2_source")
    show(p, w, "view refreshed after changes", LAST_ALTERED)
    run_update(p, pipeline_id)
    show(p, w, "after update 2 (expect A1 Fay, A3 closed, A4 new)", MIGRATED)

    run_update(p, pipeline_id)
    show(p, w, "after update 3, no refresh (expect unchanged)", MIGRATED)
    show(p, w, "flow_progress events", flows(pipeline_id))


if __name__ == "__main__":
    main()
