"""Skill check: does the .sql file a skill writes run as-is in a pipeline?

Fills the templates of the snapshot skills (`..._snapshot_sql` and `..._snapshot_sid_sql`; the keyed
skill's pipeline file is the sid one) with the tables the sid notebook left in dev, loads both files
into one scratch pipeline (targets `zz_skill_plain`, `zz_skill_sid`), runs one update and compares
with the notebook's `asset_dim_migrated`: the history part (up to the last legacy date) must be equal,
and so must the current rows. Then removes the scratch pipeline and its tables.
Usage: uv run python skill_check.py --profile <PROFILE> --warehouse <ID> --cutover 2025-05-01
"""

import argparse
from pathlib import Path

from probe import SCHEMA, cli, create_pipeline, run_update, show, sql, upload

SKILLS = Path(__file__).parents[2] / "skills"
COLS = ["asset_id", "asset_name", "asset_owner"]
ROW_HASH = "sha2(concat_ws('|', " + ", ".join(f"coalesce({c}, '<null>')" for c in COLS) + "), 256)"
NAME = "zz-probe-skill-check"


def fill(skill: str, target: str) -> str:
    """The skill's template with the sid notebook's tables, as the skill would write it."""
    catalog, schema = SCHEMA.split(".")
    values = {
        "target": target, "legacy_table": f"{SCHEMA}.asset_dim_legacy", "source_table": f"{SCHEMA}.asset_source",
        "source_catalog": catalog, "source_schema": schema, "source_name": "asset_source",
        "keys": "asset_id", "columns": ", ".join(COLS), "start_col": "start_date", "end_col": "end_date",
        "u_columns": ", ".join(f"u.{c}" for c in COLS), "l_columns": ", ".join(f"l.{c}" for c in COLS),
        "sid": "asset_sid", "row_hash": ROW_HASH,
    }
    text = (SKILLS / skill / "assets/template.sql").read_text()
    for k, v in values.items():
        text = text.replace("{{" + k + "}}", v)
    assert "{{" not in text
    return text


def compare(target: str, columns: str, cutover: str) -> str:
    history = f"""__START_AT <= TIMESTAMP'{cutover}'"""
    end = f"CASE WHEN __END_AT <= TIMESTAMP'{cutover}' THEN __END_AT END"
    return f"""
SELECT '{target} history' AS part,
  (SELECT count(*) FROM (SELECT {columns}, __START_AT, {end} FROM {SCHEMA}.asset_dim_migrated WHERE {history}
                         EXCEPT ALL SELECT {columns}, __START_AT, {end} FROM {SCHEMA}.{target} WHERE {history})) AS only_notebook,
  (SELECT count(*) FROM (SELECT {columns}, __START_AT, {end} FROM {SCHEMA}.{target} WHERE {history}
                         EXCEPT ALL SELECT {columns}, __START_AT, {end} FROM {SCHEMA}.asset_dim_migrated WHERE {history})) AS only_skill
UNION ALL
SELECT '{target} current',
  (SELECT count(*) FROM (SELECT {columns} FROM {SCHEMA}.asset_dim_migrated WHERE __END_AT IS NULL
                         EXCEPT ALL SELECT {columns} FROM {SCHEMA}.{target} WHERE __END_AT IS NULL)),
  (SELECT count(*) FROM (SELECT {columns} FROM {SCHEMA}.{target} WHERE __END_AT IS NULL
                         EXCEPT ALL SELECT {columns} FROM {SCHEMA}.asset_dim_migrated WHERE __END_AT IS NULL))
"""


def teardown(p: str, w: str) -> None:
    ids = [x["pipeline_id"] for x in cli(p, "pipelines", "list-pipelines", "--filter", f"name LIKE '{NAME}'")]
    for pid in ids:
        cli(p, "pipelines", "delete", pid)
    for t in ("zz_skill_plain", "zz_skill_sid"):
        sql(p, w, f"DROP TABLE IF EXISTS {SCHEMA}.{t}")
    catalog, schema = SCHEMA.split(".")
    owners = [pid.replace("-", "_") for pid in ids]
    for (name,) in sql(p, w, f"SELECT table_name FROM {catalog}.information_schema.tables WHERE table_schema = '{schema}'"):
        if any(name == f"event_log_{o}" or name.startswith(f"__materialization_mat_{o}_") for o in owners):
            sql(p, w, f"DROP TABLE IF EXISTS {SCHEMA}.`{name}`")
            print("--- dropped", name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--warehouse", required=True)
    parser.add_argument("--cutover", required=True)
    a = parser.parse_args()
    p, w = a.profile, a.warehouse

    user = cli(p, "current-user", "me")["userName"]
    remotes = []
    for skill, target in [("bronze-publish-scd2-autocdc-backfill-snapshot-sql", "zz_skill_plain"),
                          ("bronze-publish-scd2-autocdc-backfill-snapshot-sid-sql", "zz_skill_sid")]:
        local = Path(__file__).parent / f"skill_check_{target}.sql"
        local.write_text(fill(skill, target), newline="\n")
        remote = f"/Workspace/Users/{user}/poc/scd2-history-migration/skill_check/{target}.sql"
        upload(p, str(local), remote)
        remotes.append(remote)
    pipeline_id = create_pipeline(p, NAME, remotes)
    print(f"--- pipeline {pipeline_id}")
    if run_update(p, pipeline_id) == "COMPLETED":
        show(p, w, "zz_skill_sid", f"SELECT asset_sid, asset_id, asset_owner, __START_AT, __END_AT FROM {SCHEMA}.zz_skill_sid ORDER BY asset_id, __START_AT")
        show(p, w, "rows only in the notebook's table / only in the skill's (all 0 = equal)",
             compare("zz_skill_plain", ", ".join(COLS), a.cutover) + "UNION ALL"
             + compare("zz_skill_sid", "asset_sid, " + ", ".join(COLS), a.cutover))
    teardown(p, w)


if __name__ == "__main__":
    main()
