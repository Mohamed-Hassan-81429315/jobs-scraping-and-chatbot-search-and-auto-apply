#!/usr/bin/env bash
# JobScope daily pipeline:
#   scrape -> validate jobs.json -> import into MySQL -> index in Elasticsearch
set -uo pipefail

ROOT="${JOBSCOPE_ROOT:-$HOME/Jobs and chatbot}"
cd "$ROOT" || exit 1
mkdir -p logs
LOG="$ROOT/logs/pipeline-$(date +%F).log"
exec > >(tee -a "$LOG") 2>&1

# Only one run at a time (a manual run and the timer can't overlap).
exec 9>"$ROOT/.pipeline.lock"
if ! flock -n 9; then
  echo "Another run is in progress; exiting."
  exit 0
fi

# Stray DB_* variables would override Laravel's .env file.
unset DB_CONNECTION DB_HOST DB_PORT DB_DATABASE DB_USERNAME DB_PASSWORD DB_URL DB_SOCKET

PY="$ROOT/venv/bin/python"
JSON="$ROOT/jobs.json"
FAILED=()
START=$(date +%s)

echo "===== $(date -Is) pipeline start ====="

run_step() {
  local name="$1"
  shift
  echo "--- $name"
  if timeout 4h "$@"; then
    echo "ok: $name"
  else
    echo "FAILED: $name (exit $?)"
    FAILED+=("$name")
    return 1
  fi
}

# Pre-flight: Elasticsearch must answer (try to start the container once).
if ! curl -fsS --max-time 5 http://127.0.0.1:9200 >/dev/null 2>&1; then
  echo "Elasticsearch not reachable; trying to start container jobs-es"
  docker start jobs-es >/dev/null 2>&1 || true
  sleep 20
fi

# Keep a backup so a bad run can never destroy the collected data.
[ -f "$JSON" ] && cp -p "$JSON" "$JSON.bak"

# 1) Scrape. A failing scraper must not stop the others.
run_step "aggregator" "$PY" job_aggregator.py --epam-limit 0
run_step "smartrecruiters" "$PY" run_smartrecruiters.py
# LinkedIn + Indeed + Glassdoor through the licensed JSearch API (needs JSEARCH_API_KEY
# in common_platforms.env). Exits 2 on a bad key / used-up quota, so it shows up as FAILED.
run_step "linkedin-indeed-glassdoor" "$PY" scrape_jobboards.py \
  --platforms linkedin,indeed,glassdoor --date-posted 3days --max-requests 20

# 2) Validate the JSON before it touches the database.
if ! "$PY" - "$JSON" <<'PYEOF'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
assert isinstance(data.get("jobs"), list) and data["jobs"], "no jobs in file"
print(f"jobs.json valid: {len(data['jobs'])} jobs")
PYEOF
then
  echo "jobs.json is invalid; restoring the backup and skipping import"
  [ -f "$JSON.bak" ] && cp -p "$JSON.bak" "$JSON"
  FAILED+=("validate")
fi

# 3) Import into MySQL, then 4) refresh the search index.
if [[ " ${FAILED[*]} " != *" validate "* ]]; then
  cd "$ROOT/jobs-backend" || exit 1
  if run_step "import" php artisan jobs:import "$JSON" --no-interaction; then
    run_step "index" php artisan jobs:index --no-interaction
  fi
  cd "$ROOT" || exit 1
fi

# Keep 30 days of logs.
find "$ROOT/logs" -name 'pipeline-*.log' -mtime +30 -delete

echo "===== finished in $(( $(date +%s) - START ))s; failed steps: ${FAILED[*]:-none} ====="
[ ${#FAILED[@]} -eq 0 ]
