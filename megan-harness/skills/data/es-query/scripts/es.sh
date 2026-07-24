#!/usr/bin/env bash
# Elasticsearch read-only query wrapper.
# 실제 ES 호출은 cde-skills 의 data/elasticsearch/scripts/es_query.py 에 위임.

set -euo pipefail

VAULT="${OBSIDIAN_BASE:-${HOME}/Documents/Obsidian Vault}"
SAVE_SLUG=""
SIZE=10

CANDIDATES=(
    "${HOME}/.claude/skills/data/elasticsearch/scripts/es_query.py"
    "${HOME}/.claude/skills/cde-skills/skills/data/elasticsearch/scripts/es_query.py"
    "${HOME}/work/cde/cde-skills/skills/data/elasticsearch/scripts/es_query.py"
)
ES_SCRIPT=""
for c in "${CANDIDATES[@]}"; do
    if [[ -f "$c" ]]; then ES_SCRIPT="$c"; break; fi
done
if [[ -z "$ES_SCRIPT" ]]; then
    echo "es_query.py not found. ai-env sync 후 재시도." >&2
    exit 2
fi

# 인자 그대로 전달 (--save 만 가로채기)
PASS_ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --save)
            SAVE_SLUG="$2"; shift 2;;
        --size)
            SIZE="$2"; PASS_ARGS+=(--size "$2"); shift 2;;
        *)
            PASS_ARGS+=("$1"); shift;;
    esac
done

SCRIPT_DIR="$(dirname "$ES_SCRIPT")"
VENV_PY="${SCRIPT_DIR}/../.venv/bin/python"
[[ -x "$VENV_PY" ]] || VENV_PY="python3"

TMP_OUT="$(mktemp)"
trap 'rm -f "$TMP_OUT"' EXIT
"$VENV_PY" "$ES_SCRIPT" "${PASS_ARGS[@]}" > "$TMP_OUT"
cat "$TMP_OUT"

if [[ -n "$SAVE_SLUG" ]]; then
    DATE_KST="$(TZ='Asia/Seoul' date +%Y-%m-%d)"
    HHMM="$(TZ='Asia/Seoul' date +%H%M)"
    YM="$(TZ='Asia/Seoul' date +%Y-%m)"
    NOTE_DIR="${VAULT}/90_journal/04_sessions/${YM}"
    mkdir -p "$NOTE_DIR"
    NOTE="${NOTE_DIR}/${DATE_KST}-${HHMM}-${SAVE_SLUG}-es.md"
    {
        echo "---"
        echo "date: ${DATE_KST}"
        echo "type: es"
        echo "tags: [elasticsearch, query]"
        echo "---"
        echo
        echo "# ES — ${SAVE_SLUG}"
        echo
        echo "## 결과 (size ${SIZE})"
        cat "$TMP_OUT"
    } > "$NOTE"
    echo "saved: $NOTE" >&2
fi
