#!/bin/bash
# Run the Cline CLI, persist the raw JSON stream, and emit a readable summary.
#
# Inputs (same as run_cline_task.sh):
#   $1 (required): prompt to send to Cline
#   $2... (optional): extra args passed through to Cline
# Environment:
#   DEBUG=1                Enable debug logging to stderr and debug log file
#   CLINE_STREAM_LOG_PATH  Raw log destination; defaults to $PROJECT_ROOT/script_log/cline_<timestamp>_<TASK_ID>.log
#   SCRIPT_LOG_DIR         Directory for debug logs (default: $PROJECT_ROOT/script_log)
#   TASK_ID                Used to name the log file (set by cli_executor.py)
#
# Behavior:
#   - Runs Cline, saves the raw log to $PROJECT_ROOT/script_log, then prints it back to stdout.
#   - Uses cat + jq on the saved log to print human-friendly lines and a summary.
#   - Log filename default: cline_<YYYYmmdd_HHMMSS>_<TASK_ID>.log (TASK_ID from env or "unknown").
#   - If a summary is found, exits 0 even if Cline returned non-zero.

set -euo pipefail

DEBUG="${DEBUG:-}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SCRIPT_LOG_DIR="${SCRIPT_LOG_DIR:-$PROJECT_ROOT/script_log}"
mkdir -p "$SCRIPT_LOG_DIR"
DEBUG_LOG_PATH="$SCRIPT_LOG_DIR/run_cline_task_v1.debug.log"

log_debug() {
  [[ -z "$DEBUG" ]] && return
  mkdir -p "$SCRIPT_LOG_DIR"
  local msg="$1"
  echo "$msg" >&2
  printf '%s\n' "$msg" >>"$DEBUG_LOG_PATH"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command not found: $1" >&2
    exit 1
  fi
}

require_cmd cline
require_cmd jq
require_cmd cat
require_cmd date

PROMPT="${1:-}"
if [[ -z "$PROMPT" ]]; then
  echo "Usage: $0 \"<prompt>\" [additional cline args...]" >&2
  exit 1
fi
shift || true

RAW_TASK_ID="${TASK_ID:-unknown}"
SAFE_TASK_ID="${RAW_TASK_ID//[^A-Za-z0-9._-]/_}"
TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"
DEFAULT_LOG_NAME="cline_${TIMESTAMP}_${SAFE_TASK_ID}.log"
LOG_PATH="${CLINE_STREAM_LOG_PATH:-$SCRIPT_LOG_DIR/$DEFAULT_LOG_NAME}"
mkdir -p "$(dirname "$LOG_PATH")"

log_debug "[RUN_CLINE_V1][debug] prompt: $PROMPT"
log_debug "[RUN_CLINE_V1][debug] extra args: $*"
log_debug "[RUN_CLINE_V1][debug] log path: $LOG_PATH"
log_debug "[RUN_CLINE_V1][debug] task id: $SAFE_TASK_ID"

# Run Cline, persist raw log, then echo the raw log.
cline "$@" -F json -y --mode act "$PROMPT" >"$LOG_PATH"
status=$?
cat "$LOG_PATH"

# Render human-friendly lines and summary from the raw log.
JSON_LINES="$(cat "$LOG_PATH" | grep -E '^[[:space:]]*[{\[]' || true)"

if [[ -n "$JSON_LINES" ]]; then
  printf '%s\n' "$JSON_LINES" | jq -r '
    select(.text) |
    "[\(.say // "log")] \(.text | gsub("\\n"; "\n"))"
  ' 2>/dev/null
fi

SUMMARY_TEXT="$(
  printf '%s\n' "$JSON_LINES" | jq -r '
    select(.say == "completion_result") | .text
  ' 2>/dev/null | sed "s/\\\\n/\\n/g"
)"

if [[ -n "$SUMMARY_TEXT" ]]; then
  printf 'SUMMARY: %s\n' "$SUMMARY_TEXT"
  status=0
fi

log_debug "[RUN_CLINE_V1][debug] final exit status: $status"

exit "$status"
