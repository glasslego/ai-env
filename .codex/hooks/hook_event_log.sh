#!/usr/bin/env bash
# hook_event_log.sh — append Codex/Claude hook events to a local jsonl log.

set -euo pipefail

PROJECT_ROOT=""
if git rev-parse --show-toplevel &>/dev/null; then
    PROJECT_ROOT="$(git rev-parse --show-toplevel)"
else
    PROJECT_ROOT="$PWD"
fi

LOG_DIR="${PROJECT_ROOT}/.claude/logs/hooks"
mkdir -p "$LOG_DIR"

INPUT="$(cat || true)"
TS="$(date -Iseconds 2>/dev/null || date '+%Y-%m-%dT%H:%M:%S%z')"

_esc() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\t/\\t/g'; }

printf '{"ts":"%s","cwd":"%s","event":%s}\n' \
    "$(_esc "$TS")" \
    "$(_esc "$PROJECT_ROOT")" \
    "${INPUT:-{}}" \
    >> "${LOG_DIR}/events.jsonl"
