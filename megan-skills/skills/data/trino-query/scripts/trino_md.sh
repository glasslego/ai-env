#!/usr/bin/env bash
# Trino query → markdown table (옵시디언 노트 임베드용).
# 실제 Trino 실행은 cde-skills 의 data/trino/scripts/trino_query.py 에 위임.
#
# Usage:
#   trino_md.sh "SELECT 1"
#   trino_md.sh -f query.sql --save my-slug --limit 100

set -euo pipefail

VAULT="${OBSIDIAN_BASE:-${HOME}/Documents/Obsidian Vault}"
SAVE_SLUG=""
LIMIT=50
SQL=""
SQL_FILE=""
CATALOG=""
SCHEMA=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -f|--file)
            SQL_FILE="$2"; shift 2;;
        --save)
            SAVE_SLUG="$2"; shift 2;;
        --limit)
            LIMIT="$2"; shift 2;;
        --catalog|-c)
            CATALOG="$2"; shift 2;;
        --schema)
            SCHEMA="$2"; shift 2;;
        -h|--help)
            sed -n '2,8p' "$0"; exit 0;;
        *)
            SQL="$1"; shift;;
    esac
done

# trino_query.py 위치 탐색
CANDIDATES=(
    "${HOME}/.claude/skills/data/trino/scripts/trino_query.py"
    "${HOME}/.claude/skills/cde-skills/skills/data/trino/scripts/trino_query.py"
    "${HOME}/work/cde/cde-skills/skills/data/trino/scripts/trino_query.py"
)
TRINO_SCRIPT=""
for c in "${CANDIDATES[@]}"; do
    if [[ -x "$c" || -f "$c" ]]; then
        TRINO_SCRIPT="$c"; break
    fi
done
if [[ -z "$TRINO_SCRIPT" ]]; then
    echo "trino_query.py not found in any of:" >&2
    printf '  %s\n' "${CANDIDATES[@]}" >&2
    echo "→ ai-env sync 후 재시도하거나 cde-skills 가 설치되었는지 확인." >&2
    exit 2
fi

# SQL 입력 결정
if [[ -n "$SQL_FILE" ]]; then
    if [[ ! -f "$SQL_FILE" ]]; then
        echo "sql file not found: $SQL_FILE" >&2; exit 2
    fi
    SQL="$(cat "$SQL_FILE")"
fi
if [[ -z "$SQL" ]]; then
    echo "SQL not provided" >&2; exit 2
fi

# 위임 실행 (cde-skills/data/trino 의 인자 컨벤션 사용)
TMP_OUT="$(mktemp)"
trap 'rm -f "$TMP_OUT"' EXIT

# 우선 인접 venv python 시도, 없으면 시스템 python
SCRIPT_DIR="$(dirname "$TRINO_SCRIPT")"
VENV_PY="${SCRIPT_DIR}/../.venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then VENV_PY="python3"; fi

# LIMIT 을 SQL 에 자동 부착 (이미 LIMIT 있으면 미부착)
if ! echo "$SQL" | grep -qiE '\blimit\b'; then
    SQL="${SQL%;}
LIMIT ${LIMIT}"
fi
TRINO_ARGS=(query --sql "$SQL")
[[ -n "$CATALOG" ]] && TRINO_ARGS+=(--catalog "$CATALOG")
[[ -n "$SCHEMA" ]] && TRINO_ARGS+=(--schema "$SCHEMA")

"$VENV_PY" "$TRINO_SCRIPT" "${TRINO_ARGS[@]}" > "$TMP_OUT" || {
    echo "trino_query.py 실행 실패." >&2
    cat "$TMP_OUT" >&2
    exit 1
}
cat "$TMP_OUT"

# vault 저장 옵션
if [[ -n "$SAVE_SLUG" ]]; then
    DATE_KST="$(TZ='Asia/Seoul' date +%Y-%m-%d)"
    HHMM="$(TZ='Asia/Seoul' date +%H%M)"
    YM="$(TZ='Asia/Seoul' date +%Y-%m)"
    NOTE_DIR="${VAULT}/90_journal/04_sessions/${YM}"
    mkdir -p "$NOTE_DIR"
    NOTE="${NOTE_DIR}/${DATE_KST}-${HHMM}-${SAVE_SLUG}-trino.md"
    {
        echo "---"
        echo "date: ${DATE_KST}"
        echo "type: trino"
        echo "tags: [trino, query]"
        echo "---"
        echo
        echo "# Trino — ${SAVE_SLUG}"
        echo
        echo "## SQL"
        echo '```sql'
        echo "$SQL"
        echo '```'
        echo
        echo "## 결과 (limit ${LIMIT})"
        cat "$TMP_OUT"
    } > "$NOTE"
    echo "saved: $NOTE" >&2
fi
