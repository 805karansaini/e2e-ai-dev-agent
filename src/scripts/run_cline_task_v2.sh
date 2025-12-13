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
#   - Uses jq on the saved log to extract a summary.
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


# cline config set act-mode-open-router-model-id=openai/gpt-5-mini
# cline config set plan-mode-open-router-model-id=openai/gpt-5-mini

# cline config set act-mode-open-router-model-id=openai/gpt-5.1
# cline config set plan-mode-open-router-model-id=openai/gpt-5.1

# cline config set act-mode-open-router-model-id=anthropic/claude-haiku-4.5
# cline config set plan-mode-open-router-model-id=anthropic/claude-haiku-4.5

# cline config set act-mode-open-router-model-id=amazon/nova-2-lite-v1:free
# cline config set plan-mode-open-router-model-id=amazon/nova-2-lite-v1:free


log_debug "[RUN_CLINE_V1][debug] prompt: $PROMPT"
log_debug "[RUN_CLINE_V1][debug] extra args: $*"
log_debug "[RUN_CLINE_V1][debug] log path: $LOG_PATH"
log_debug "[RUN_CLINE_V1][debug] task id: $SAFE_TASK_ID"
log_debug "[RUN_CLINE_V1][debug] command: cline -y --mode plan -F json -o \"PROMPT\" $*"

# Run Cline, persist raw log, then echo the raw log.
# Use tee so we persist the raw JSON stream and also echo it to stdout.
# With `set -e` and `set -o pipefail`, run the pipeline in a conditional context
# so we can capture cline's exit code without aborting the script.
status=0
if ! cline -y "$PROMPT" "$@" --mode plan -F json | tee "$LOG_PATH"; then
  # Preserve the original cline exit code (not tee's), but also fail if tee failed
  # (since persisting logs is required).
  cline_status=${PIPESTATUS[0]}
  tee_status=${PIPESTATUS[1]}
  if [[ "${tee_status:-0}" -ne 0 ]]; then
    status=$tee_status
  else
    status=$cline_status
  fi
fi

# Extract summary from the raw log.
# We drop any preamble before the first JSON object/array in case cline emits
# non-JSON lines before the JSON stream begins.
SUMMARY_TEXT="$(
  sed -n '/^[[:space:]]*[{[]/,$p' "$LOG_PATH" | jq -nr '
    reduce inputs as $i (
      null;
      if ($i.say == "completion_result") then
        ($i.text // $i.content // "")
      else
        .
      end
    )
    | select(. != null and . != "")
    | gsub("\\n"; "\n")
  ' 2>/dev/null || true
)"

if [[ -n "$SUMMARY_TEXT" && "$SUMMARY_TEXT" != "null" ]]; then
  printf 'SUMMARY: %s\n' "$SUMMARY_TEXT"
  status=0
fi

log_debug "[RUN_CLINE_V1][debug] final exit status: $status"

exit "$status"
