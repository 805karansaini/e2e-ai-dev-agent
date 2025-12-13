#!/usr/bin/env bash
set -euo pipefail

# Enhanced Cline CLI Log Renderer
# Produces human-readable output from multi-line JSON logs

LOG_PATH="${1:-}"

if [[ -z "$LOG_PATH" ]]; then
  echo "Usage: $(basename "$0") <path-to-log>" >&2
  exit 1
fi

if [[ ! -f "$LOG_PATH" ]]; then
  echo "Log file not found: $LOG_PATH" >&2
  exit 1
fi

# Extract JSON stream (skip any non-JSON preamble)
json_stream="$(awk 'seen || /^[[:space:]]*[{[]/ {seen=1; print}' "$LOG_PATH")"

# Terminal colors
BOLD='\033[1m'
DIM='\033[2m'
CYAN='\033[36m'
GREEN='\033[32m'
YELLOW='\033[33m'
BLUE='\033[34m'
MAGENTA='\033[35m'
RESET='\033[0m'

echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}  🤖 CLINE CLI EXECUTION REPORT${RESET}"
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${DIM}Generated from: $LOG_PATH${RESET}"
echo ""

if [[ -z "$json_stream" ]]; then
  echo "No valid JSON found in log file"
  exit 0
fi

printf '%s\n' "$json_stream" | jq -r '

# Helper function to unescape strings
def unescape:
  gsub("\\\\n"; "\n") | gsub("\\\\t"; "\t") | gsub("\\\\r"; "\r") |
  gsub("\\\\\""; "\"") | gsub("\\\\\\\\"; "\\");

# Helper function to format timestamps
def format_time:
  if .ts then
    (.ts / 1000 | strftime("%H:%M:%S"))
  else
    ""
  end;

# Process each log entry
if .say == "text" and (.text | test("=== .* TASK PROMPT ===")) then
  "\n\u001b[1m\u001b[34m╔═══════════════════════════════════════════════════════════════╗\u001b[0m\n\u001b[1m\u001b[34m║                     📋 TASK REQUESTED                         ║\u001b[0m\n\u001b[1m\u001b[34m╚═══════════════════════════════════════════════════════════════╝\u001b[0m\n\n\(.text | unescape)\n"

elif .say == "text" and (.text | length) > 0 then
  if (.text | test("^Assumptions made:")) then
    "\n\u001b[2m┌─ 💭 Agent Reasoning ─────────────────────────────────────────┐\u001b[0m\n\(.text | unescape)\n\u001b[2m└──────────────────────────────────────────────────────────────┘\u001b[0m\n"
  else
    "\n\u001b[36m💬 Agent:\u001b[0m \(.text | unescape)\n"
  end

elif .say == "command" then
  "\n\u001b[1m\u001b[33m⚡ Executing:\u001b[0m \u001b[35m\(.text)\u001b[0m"

elif .say == "command_output" and (.text | length) > 50 then
  "\n\u001b[2m   Output (truncated):\u001b[0m\n\u001b[2m\(.text | unescape | split("\n") | .[0:5] | join("\n"))\n   ...\u001b[0m\n"

elif .say == "command_output" then
  "\n\u001b[2m   Output:\u001b[0m \(.text | unescape)\n"

elif .say == "task_progress" then
  "\n\u001b[1m\u001b[32m📊 Progress Checklist:\u001b[0m\n\(.text | unescape | gsub("- \\[ \\]"; "\u001b[0m❌ ") | gsub("- \\[x\\]"; "\u001b[32m✅\u001b[0m "))\n"

elif .say == "checkpoint_created" then
  "\n\u001b[2m───────────────────────────── ⏸️  Checkpoint ─────────────────────────────\u001b[0m\n"

elif .say == "completion_result" then
  "\n\u001b[1m\u001b[32m╔═══════════════════════════════════════════════════════════════╗\u001b[0m\n\u001b[1m\u001b[32m║                    ✅ TASK COMPLETED                           ║\u001b[0m\n\u001b[1m\u001b[32m╚═══════════════════════════════════════════════════════════════╝\u001b[0m\n\n\(.text | unescape)\n"

elif .say == "tool" then
  (try (.text | fromjson) catch {} |
   if .tool == "newFileCreated" then
     "\n\u001b[34m📄 Created:\u001b[0m \(.path)"
   elif .tool then
     "\n\u001b[34m🔧 Tool:\u001b[0m \(.tool)"
   else
     ""
   end)

elif .say == "api_req_started" then
  (try (.text | fromjson) catch {} |
   if .tokensIn then
     "\n\u001b[2m   [API: \(.tokensIn // 0) tokens in, \(.tokensOut // 0) tokens out]\u001b[0m"
   else
     ""
   end)

else
  ""
end
' 2>/dev/null || true

echo ""
echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${DIM}End of report${RESET}"
