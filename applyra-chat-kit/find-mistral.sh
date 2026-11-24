#!/usr/bin/env bash
# Lists every remaining Mistral reference in the project (code, env files, configs, docs).
# Usage: ./find-mistral.sh "/home/engineer-mohamed-hassan/Jobs and chatbot"
ROOT="${1:-/home/engineer-mohamed-hassan/Jobs and chatbot}"
grep -rniI "mistral" "$ROOT" \
  --exclude-dir={node_modules,vendor,venv,.next,.git,storage,.chat-backup-*,.kit-backup-*} \
  --exclude="*.lock" --exclude="package-lock.json" --exclude="project_architecture.txt" \
  | cut -c1-220 || true
echo "-- (no lines above = no Mistral references left)"
