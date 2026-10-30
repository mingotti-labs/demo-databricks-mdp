#!/usr/bin/env bash
# Probe P1: does a deployed pipeline accept a new default schema and keep working?
# Usage: bash p1.sh <profile>, run from this folder. Creates one scratch
# pipeline and one table (mdp_dev.pattern_bronze.zz_p1_default_schema).
set -euo pipefail
P=$1
DIR=/Workspace/Users/handsonessential@gmail.com/poc/single-silver-landing-schema
json() { python -c "import sys,json;print(json.load(sys.stdin)$1)" | tr -d '\r'; }
spec() {
  cat <<JSON
{"name":"zz-probe-p1-default-schema","catalog":"mdp_dev","schema":"$1","serverless":true,"continuous":false,
 "libraries":[{"file":{"path":"$DIR/p1_pipeline.py"}}]}
JSON
}
run() {
  U=$(databricks pipelines start-update "$ID" --profile "$P" -o json | json "['update_id']")
  while true; do
    S=$(databricks pipelines get-update "$ID" "$U" --profile "$P" -o json | json "['update']['state']")
    case $S in COMPLETED|FAILED|CANCELED) echo "update $U: $S"; break;; esac
    sleep 15
  done
}

databricks workspace mkdirs "$DIR" --profile "$P"
databricks workspace import "$DIR/p1_pipeline.py" --file p1_pipeline.py --format SOURCE --language PYTHON --overwrite --profile "$P"
ID=$(databricks pipelines create --json "$(spec pattern_bronze)" --profile "$P" -o json | json "['pipeline_id']")
echo "pipeline $ID"
run
echo "--- change default schema to pattern_bronze_publish"
databricks pipelines update "$ID" --json "$(spec pattern_bronze_publish)" --profile "$P" && echo "update accepted"
echo "schema now: $(databricks pipelines get "$ID" --profile "$P" -o json | json "['spec']['schema']")"
run
echo "table pipelineId: $(databricks tables get mdp_dev.pattern_bronze.zz_p1_default_schema --profile "$P" -o json | json "['properties'].get('pipelines.pipelineId')")"
