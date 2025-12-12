#!/bin/bash
# Stream Cline CLI output in JSON format and emit a summary.
# Usage: run_cline_task.sh "<prompt>" [additional cline args...]
# Debug: set DEBUG=1 to print internal details.

set -euo pipefail

DEBUG="${DEBUG:-}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SCRIPT_LOG_DIR="${SCRIPT_LOG_DIR:-$PROJECT_ROOT/script_log}"
DEBUG_LOG_PATH="$SCRIPT_LOG_DIR/run_cline_task.debug.log"

log_debug() {
  if [[ -z "$DEBUG" ]]; then
    return
  fi

  mkdir -p "$SCRIPT_LOG_DIR"
  local msg="$1"
  echo "$msg" >&2
  printf '%s\n' "$msg" >>"$DEBUG_LOG_PATH"
}

PROMPT="${1:-}"
if [[ -z "$PROMPT" ]]; then
  echo "Usage: $0 \"<prompt>\" [additional cline args...]" >&2
  exit 1
fi
shift || true

# Debug: show invocation details and where logs will be stored.
log_debug "[RUN_CLINE_SH][debug] cwd: $(pwd)"
log_debug "[RUN_CLINE_SH][debug] prompt: $PROMPT"
log_debug "[RUN_CLINE_SH][debug] extra args: $*"
log_debug "[RUN_CLINE_SH][debug] env CLINE_STREAM_LOG_PATH: ${CLINE_STREAM_LOG_PATH:-<unset>}"
log_debug "[RUN_CLINE_SH][debug] DEBUG=1"

# Optional: set CLINE_STREAM_LOG_PATH to tee output to a known file.
LOG_PATH="${CLINE_STREAM_LOG_PATH:-}"
if [[ -n "$LOG_PATH" ]]; then
  mkdir -p "$(dirname "$LOG_PATH")"
else
  LOG_PATH="$(mktemp -t cline-task-log.XXXXXX)"
fi

echo "[RUN_CLINE_SH][info] cline log path: $LOG_PATH" >&2
log_debug "[RUN_CLINE_SH][debug] log file will be overwritten"

# Run Cline with enforced json output; stream everything and capture exit code.
if command -v jq >/dev/null 2>&1; then
  log_debug "[RUN_CLINE_SH][debug] using jq to compact JSON; preserving non-JSON lines"
  # Allow non-JSON lines to pass through by buffering and attempting per-line parses.
  # We also emit problematic lines to stderr in debug mode.
  cline "$@" -F json -y --mode act "$PROMPT" | \
    while IFS= read -r line; do
      if [[ "$line" =~ ^[[:space:]]*[{[] ]]; then
        if ! printf '%s\n' "$line" | jq -c . 2>/dev/null; then
          log_debug "[debug] non-json/parse-fail: $line"
          printf '%s\n' "$line"
        fi
      else
        printf '%s\n' "$line"
      fi
    done | tee "$LOG_PATH"
  status=${PIPESTATUS[0]}
else
  log_debug "[RUN_CLINE_SH][debug] jq not found; streaming raw output"
  cline "$@" -F json -y --mode act "$PROMPT" | tee "$LOG_PATH"
  status=${PIPESTATUS[0]}
fi

# Emit a human-readable summary if jq is available; leave streaming intact.
if command -v jq >/dev/null 2>&1; then
  JSON_LINES="$(grep -E '^[[:space:]]*[{\[]' "$LOG_PATH" || true)"

  # Pretty, human-readable log rendering (optional; still keep raw log).
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
    log_debug "[RUN_CLINE_SH][debug] summary detected; overriding status to 0 (was $status)"
    # Treat runs with a summary as success even if the process returned non-zero.
    status=0
  else
    log_debug "[RUN_CLINE_SH][debug] no summary detected"
  fi
fi

log_debug "[RUN_CLINE_SH][debug] final exit status: $status"

exit "$status"
