"""Probe P1 (pattern-scd2-history-migration): does AUTO CDC ONCE from a batch
temporary view work in SQL, land the legacy dates in __START_AT/__END_AT, and
write nothing on the second update?

Creates in mdp_dev.pattern_bronze_publish: zz_p1_legacy (plain table), the
scratch pipeline zz-probe-p1-backfill-once and its table zz_p1_migrated (3 slots).
Usage: uv run python p1.py --profile <PROFILE> --warehouse <WAREHOUSE_ID>
"""

import argparse
from pathlib import Path

from probe import SCHEMA, cli, create_pipeline, run_update, show, sql, upload

LEGACY = f"""
CREATE OR REPLACE TABLE {SCHEMA}.zz_p1_legacy AS
SELECT * FROM VALUES
  ('A1', 'Pump',  'Ann', DATE'2024-01-01', DATE'2024-06-01'),
  ('A1', 'Pump',  'Bob', DATE'2024-06-01', CAST(NULL AS DATE)),
  ('A2', 'Valve', 'Cy',  DATE'2024-02-01', DATE'2025-03-01'),
  ('A3', 'Fan',   'Di',  DATE'2024-03-01', CAST(NULL AS DATE))
  AS t(asset_id, asset_name, asset_owner, start_date, end_date)
"""

COMPARE = f"""
SELECT l.asset_id, l.asset_owner, l.start_date, l.end_date, m.__START_AT, m.__END_AT,
       CAST(l.start_date AS TIMESTAMP) <=> m.__START_AT
       AND CAST(l.end_date AS TIMESTAMP) <=> m.__END_AT AS dates_match
FROM {SCHEMA}.zz_p1_legacy l
FULL JOIN {SCHEMA}.zz_p1_migrated m
  ON l.asset_id = m.asset_id AND CAST(l.start_date AS TIMESTAMP) = m.__START_AT
ORDER BY 1, 3
"""


def flow_rows(pipeline_id: str) -> str:
    return f"""
SELECT origin.update_id, origin.flow_name,
       details:flow_progress.status AS status,
       details:flow_progress.metrics.num_output_rows AS rows_out, timestamp
FROM event_log('{pipeline_id}')
WHERE event_type = 'flow_progress' AND origin.flow_name IS NOT NULL
ORDER BY timestamp
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--warehouse", required=True)
    a = parser.parse_args()

    user = cli(a.profile, "current-user", "me")["userName"]
    remote = f"/Workspace/Users/{user}/poc/scd2-history-migration/p1_pipeline.sql"
    sql(a.profile, a.warehouse, LEGACY)
    upload(a.profile, str(Path(__file__).parent / "p1_pipeline.sql"), remote)
    pipeline_id = create_pipeline(a.profile, "zz-probe-p1-backfill-once", [remote])
    print(f"--- pipeline {pipeline_id}")

    if run_update(a.profile, pipeline_id) != "COMPLETED":
        return
    show(a.profile, a.warehouse, "legacy vs migrated after update 1", COMPARE)
    run_update(a.profile, pipeline_id)
    show(a.profile, a.warehouse, "legacy vs migrated after update 2", COMPARE)
    show(a.profile, a.warehouse, "flow_progress events", flow_rows(pipeline_id))


if __name__ == "__main__":
    main()
