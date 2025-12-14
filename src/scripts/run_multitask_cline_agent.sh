#!/bin/bash
# Orchestrate multiple Cline sub-agents for a multi-part development task.
# Single entrypoint for "start task" style execution outside the API layer.
# Input: ONE prompt containing the parent task + explicit subtasks. The script
# extracts subtasks, then runs each via run_cline_task_v2.sh with the parent
# prompt prepended (mirrors TaskExecutor._compose_execution_prompt).
#
# Notes/assumptions
# - Preferred input is JSON: {"task": "...", "subtasks": ["...", ...]}
# - Fallback: text prompt where a line starts with "Subtasks:" followed by
#   bullet lines beginning with "-" (subtask text after the dash is used).
# - Execution is sequential (safer for shared worktrees); pass --parallel to
#   opt into background execution.
# - All child runs flow through src/scripts/run_cline_task_v2.sh, preserving
#   logging behavior and task IDs akin to /tasks/start.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RUNNER="$SCRIPT_DIR/run_cline_task_v2.sh"
SCRIPT_LOG_DIR="${SCRIPT_LOG_DIR:-$PROJECT_ROOT/script_log}"

usage() {
  cat <<'USAGE'
Usage: run_multitask_cline_agent.sh -p "<combined prompt>" | -f prompt.txt [--parallel] [-- <extra cline args>]

The combined prompt must include the parent task and explicit subtasks.
Preferred JSON shape: {"task": "...", "subtasks": ["...", "..."]}
Fallback text: a line with "Subtasks:" followed by bullet lines starting with "-".

Options:
  -p, --prompt   Inline combined prompt string (or "-" to read from stdin).
  -f, --file     File containing the combined prompt.
  --parallel     Run subtasks concurrently (default: sequential).
  --             Everything after this is passed to run_cline_task_v2.sh.

Examples:
  run_multitask_cline_agent.sh -p '{"task":"Ship auth","subtasks":["Design DB","Implement endpoints"]}'
  run_multitask_cline_agent.sh -f plan.txt -- --mode plan
  cat plan.txt | run_multitask_cline_agent.sh -p - --parallel
USAGE
}

PROMPT_RAW=""
PARALLEL="0"
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -p|--prompt)
      PROMPT_RAW="${2:-}"; shift 2 ;;
    -f|--file)
      FILE_PATH="${2:-}"; shift 2
      if [[ ! -f "$FILE_PATH" ]]; then
        echo "[error] prompt file not found: $FILE_PATH" >&2
        exit 1
      fi
      PROMPT_RAW="$(cat "$FILE_PATH")" ;;
    --parallel)
      PARALLEL="1"; shift ;;
    --)
      shift
      EXTRA_ARGS=($@)
      break ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "[error] unknown argument: $1" >&2
      usage; exit 1 ;;
  esac
done

if [[ "$PROMPT_RAW" == "-" ]]; then
  PROMPT_RAW="$(cat)"
fi

if [[ -z "$PROMPT_RAW" ]]; then
  echo "[error] prompt is required" >&2
  usage
  exit 1
fi

if [[ ! -x "$RUNNER" ]]; then
  echo "[error] expected runner script at $RUNNER" >&2
  exit 1
fi

mkdir -p "$SCRIPT_LOG_DIR"
TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"

parse_json_prompt() {
  # Expects JSON with keys: task (string) and subtasks (array of strings)
  local json="$1"
  if ! command -v jq >/dev/null 2>&1; then
    echo "[warn] jq not available; cannot parse JSON input" >&2
    return 1
  fi
  local task subtasks
  task="$(printf '%s' "$json" | jq -r 'try .task // empty')" || return 1
  mapfile -t subtasks < <(printf '%s' "$json" | jq -r 'try .subtasks[] // empty' | sed '/^$/d') || true
  if [[ -z "$task" || ${#subtasks[@]} -eq 0 ]]; then
    return 1
  fi
  MAIN_TASK="$task"
  SUBTASKS=("${subtasks[@]}")
  return 0
}

parse_text_prompt() {
  local text="$1"
  local task_line subtasks_block
  # Task = first non-empty line before "Subtasks:"
  task_line="$(printf '%s\n' "$text" | awk 'NF {print; exit}')"
  subtasks_block="$(printf '%s\n' "$text" | sed -n '/[Ss]ubtasks:/,$p')"
  mapfile -t SUBTASKS < <(printf '%s\n' "$subtasks_block" | grep -E '^[[:space:]]*-' | sed 's/^[[:space:]]*-[[:space:]]*//')
  MAIN_TASK="${task_line:-}"
}

MAIN_TASK=""
SUBTASKS=()

# Try JSON first, fallback to text parse.
if ! parse_json_prompt "$PROMPT_RAW"; then
  parse_text_prompt "$PROMPT_RAW"
fi

if [[ -z "$MAIN_TASK" || ${#SUBTASKS[@]} -eq 0 ]]; then
  echo "[error] failed to extract main task and subtasks from prompt" >&2
  exit 1
fi

echo "[info] main task: $MAIN_TASK" >&2
echo "[info] subtasks: ${#SUBTASKS[@]}" >&2
echo "[info] logs: $SCRIPT_LOG_DIR" >&2
[[ "$PARALLEL" == "1" ]] && echo "[info] mode: parallel" >&2 || echo "[info] mode: sequential" >&2

build_prompt() {
  local idx="$1"
  local subtask="$2"
  printf '=== PARENT TASK PROMPT ===\n%s\n\n=== SUBTASK PROMPT (subtask_%s) ===\n%s\n\nYou are a focused sub-agent collaborating on a larger development effort. Provide concise progress updates, code changes, and next steps. Keep context minimal and actionable.' \
    "$MAIN_TASK" "$idx" "$subtask"
}

run_subtask() {
  local idx="$1"
  local subtask="$2"
  local prompt task_id log_path
  prompt="$(build_prompt "$idx" "$subtask")"
  task_id="subtask_${idx}"
  log_path="$SCRIPT_LOG_DIR/cline_${TIMESTAMP}_${task_id}.log"
  TASK_ID="$task_id" CLINE_STREAM_LOG_PATH="$log_path" "$RUNNER" "$prompt" "${EXTRA_ARGS[@]}"
}

PIDS=()
LABELS=()

for i in "${!SUBTASKS[@]}"; do
  idx=$((i + 1))
  subtask="${SUBTASKS[$i]}"
  echo "[info] launching subtask_${idx} -> $subtask" >&2
  if [[ "$PARALLEL" == "1" ]]; then
    run_subtask "$idx" "$subtask" & PIDS+=($!); LABELS+=("subtask_${idx}")
  else
    if run_subtask "$idx" "$subtask"; then
      echo "[info] subtask_${idx} completed successfully" >&2
    else
      echo "[warn] subtask_${idx} failed" >&2
      exit 1
    fi
  fi
done

if [[ "$PARALLEL" == "1" ]]; then
  failures=0
  for j in "${!PIDS[@]}"; do
    pid="${PIDS[$j]}"
    label="${LABELS[$j]}"
    if wait "$pid"; then
      echo "[info] $label completed successfully" >&2
    else
      echo "[warn] $label failed (exit $?)" >&2
      failures=$((failures + 1))
    fi
    echo "[info] $label log: $SCRIPT_LOG_DIR/cline_${TIMESTAMP}_${label}.log" >&2
  done
  if [[ $failures -gt 0 ]]; then
    echo "[warn] $failures subtask(s) failed" >&2
    exit 1
  fi
fi

echo "[info] all subtasks finished" >&2
exit 0
