#!/usr/bin/env bash
set -euo pipefail

# Render human-friendly lines and summary from a multi-line JSON Cline log.

LOG_PATH="${1:-}"

if [[ -z "$LOG_PATH" ]]; then
  echo "Usage: $(basename "$0") <path-to-log>" >&2
  exit 1
fi

if [[ ! -f "$LOG_PATH" ]]; then
  echo "Log file not found: $LOG_PATH" >&2
  exit 1
fi

# Drop any preamble before the first JSON object/array.
json_stream="$(awk 'seen || /^[[:space:]]*[{[]/ {seen=1; print}' "$LOG_PATH")"

if [[ -n "$json_stream" ]]; then
  printf '%s\n' "$json_stream" | jq -r '
    select(.text) |
    "[\(.say // "log")] \(.text | gsub("\\n"; "\n"))"
  ' 2>/dev/null || true
fi

summary_text="$(
  printf '%s\n' "$json_stream" | jq -r '
    select(.say == "completion_result") | .text | gsub("\\n"; "\n")
  ' 2>/dev/null
)"

if [[ -n "$summary_text" && "$summary_text" != "null" ]]; then
  printf 'SUMMARY: %s\n' "$summary_text"
fi
