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

echo "🤖 Cline CLI Task Execution Report"
echo "Generated from: $LOG_PATH"
echo ""

if [[ -n "$json_stream" ]]; then
  printf '%s\n' "$json_stream" | jq -r '
    if .say == "text" and (.text | test("=== .* TASK PROMPT ===")) then
      "═══════════════════════════════════════════════════════════════\n📋 TASK REQUESTED\n═══════════════════════════════════════════════════════════════\n\(.text | gsub("\\\\n"; "\n") | gsub("\\\\t"; "\t") | gsub("\\\\r"; "\r") | gsub("\\\\\""; "\"") | gsub("\\\\\\\\"; "\\"))"
    elif .say == "text" then
      (.text | gsub("\\\\n"; "\n") | gsub("\\\\t"; "\t") | gsub("\\\\r"; "\r") | gsub("\\\\\""; "\"") | gsub("\\\\\\\\"; "\\"))
    elif .say == "checkpoint_created" then
      "\n───────────────────────────────────────────────────────────────\n📝 PROGRESS UPDATE\n───────────────────────────────────────────────────────────────"
    elif .say == "completion_result" then
      "\n═══════════════════════════════════════════════════════════════\n✅ TASK COMPLETED\n═══════════════════════════════════════════════════════════════\n\(.text | gsub("\\\\n"; "\n") | gsub("\\\\t"; "\t") | gsub("\\\\r"; "\r") | gsub("\\\\\""; "\"") | gsub("\\\\\\\\"; "\\"))"
    elif .say == "tool" then
      "\n🔧 ACTION TAKEN\n\(try (.text | fromjson | if .tool == "newFileCreated" then "Created new file: \(.path)" else "Performed action: \(.tool)" end) catch "Executed tool operation")"
    elif .say == "task_progress" then
      "\n📊 CURRENT STATUS\n\(.text | gsub("\\\\n"; "\n") | gsub("\\\\t"; "\t") | gsub("\\\\r"; "\r") | gsub("\\\\\""; "\"") | gsub("\\\\\\\\"; "\\") | gsub("\\[ \\]"; "❌") | gsub("\\[x\\]"; "✅"))"
    elif .say == "api_req_started" then
      ""
    else
      ""
    end
  ' 2>/dev/null || true
fi
