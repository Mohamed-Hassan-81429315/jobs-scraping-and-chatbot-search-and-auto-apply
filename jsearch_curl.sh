#!/usr/bin/env bash
# One-off test of the job-data API (JSearch on RapidAPI) with curl.
# It returns jobs listed on LinkedIn, Indeed and Glassdoor through a licensed API.
#
# Usage:
#   export JSEARCH_API_KEY="your_rapidapi_key"
#   ./jsearch_curl.sh "odoo developer in Cairo"
#   ./jsearch_curl.sh "data analyst" eg        # optional 2nd arg = country code
set -euo pipefail

KEY="${JSEARCH_API_KEY:?Set JSEARCH_API_KEY first (export JSEARCH_API_KEY=...)}"
QUERY="${1:-software engineer}"
COUNTRY="${2:-}"

ARGS=(
  --data-urlencode "query=${QUERY}"
  --data-urlencode "page=1"
  --data-urlencode "num_pages=1"
  --data-urlencode "date_posted=3days"   # all | today | 3days | week | month
)
[ -n "$COUNTRY" ] && ARGS+=(--data-urlencode "country=${COUNTRY}")

if [ "${#KEY}" -lt 30 ] || [[ "${KEY,,}" == *paste* ]] || [[ "${KEY,,}" == *your_* ]]; then
  echo "JSEARCH_API_KEY looks like a placeholder ('${KEY:0:12}...'). Use the real ~50-character key from RapidAPI." >&2
  exit 2
fi

TMP=$(mktemp); trap 'rm -f "$TMP"' EXIT
HTTP=$(curl -sS -o "$TMP" -w '%{http_code}' --get "https://jsearch.p.rapidapi.com/search" \
  "${ARGS[@]}" \
  -H "X-RapidAPI-Key: ${KEY}" \
  -H "X-RapidAPI-Host: jsearch.p.rapidapi.com")
if [ "$HTTP" != "200" ]; then
  echo "HTTP $HTTP from JSearch: $(cat "$TMP")" >&2
  [ "$HTTP" = "403" ] && echo "-> Key is wrong, or this key's app is not subscribed to JSearch." >&2
  exit 1
fi
RESPONSE=$(cat "$TMP")

if command -v jq >/dev/null 2>&1; then
  # Keep only jobs published on / applicable through LinkedIn, Indeed or Glassdoor.
  echo "$RESPONSE" | jq '[.data[]
    | select(([.job_publisher] + [.apply_options[]?.publisher]
              | map(. // "" | ascii_downcase) | join(" "))
              | test("linkedin|indeed|glassdoor"))
    | {platform: .job_publisher, title: .job_title, company: .employer_name,
       city: .job_city, country: .job_country, posted: .job_posted_at_datetime_utc,
       apply: .job_apply_link}]'
else
  echo "$RESPONSE"   # install jq to get the filtered view
fi