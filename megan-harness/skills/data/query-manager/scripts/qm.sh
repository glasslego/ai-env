#!/usr/bin/env bash
# query-manager — cde-skills/data/query-manager 위임 (read-only).

set -euo pipefail

SAVE=0; SAVE_SLUG=""
NEW=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --save) SAVE=1; SAVE_SLUG="$2"; shift 2;;
        -h|--help) sed -n '2,15p' "$0"; exit 0;;
        upload|create|update|delete)
            echo "❌ mutating 명령 '$1' 차단됨." >&2; exit 2;;
        *) NEW+=("$1"); shift;;
    esac
done

[[ ${#NEW[@]} -eq 0 ]] && {
    echo "usage: qm.sh <productions|discover|queries|query ID|search-source TBL|search-sink TBL|analyze QID>" >&2
    exit 2
}

SUB="${NEW[0]}"; REST=("${NEW[@]:1}")
case "$SUB" in
    productions)   CMD="list-productions";;
    discover)      CMD="discover-productions";;
    queries)       CMD="list-queries";;
    query)         CMD="get-query";;
    search-source) CMD="search-source";;
    search-sink)   CMD="search-sink";;
    analyze)       CMD="analyze";;
    *) echo "unknown subcommand: $SUB" >&2; exit 2;;
esac

PATHS=(
    "${HOME}/.claude/skills/data/query-manager/scripts/query_manager_query.py"
    "${HOME}/work/glasslego/ai-env/cde-skills/skills/data/query-manager/scripts/query_manager_query.py"
)
DELEGATE=""
for p in "${PATHS[@]}"; do [[ -f "$p" ]] && DELEGATE="$p" && break; done
[[ -z "$DELEGATE" ]] && { echo "❌ query_manager_query.py not found." >&2; exit 2; }

if [[ $SAVE -eq 1 ]]; then
    TMP_OUT=$(mktemp -t qm-out.XXXXXX); trap 'rm -f "$TMP_OUT"' EXIT
    uv run python "$DELEGATE" "$CMD" "${REST[@]}" 2>&1 | tee "$TMP_OUT"
    [[ -s "$TMP_OUT" ]] || exit 0
    VAULT="${OBSIDIAN_BASE:-${HOME}/Documents/Obsidian Vault}"
    DATE=$(date '+%Y-%m-%d'); MONTH=$(date '+%Y-%m')
    DIR="${VAULT}/90_journal/04_sessions/${MONTH}"; mkdir -p "$DIR"
    NOTE="${DIR}/${DATE}-${SAVE_SLUG}-qm.md"
    { echo "---"; echo "date: ${DATE}"; echo "type: ops"; echo "platform: query-manager"; echo "tags: [query-manager, lineage]"; echo "---"; echo; echo "# QM ${SUB} ${REST[*]:-}"; echo; echo '```'; cat "$TMP_OUT"; echo '```'; } > "$NOTE"
    echo "💾 saved: $NOTE" >&2
else
    exec uv run python "$DELEGATE" "$CMD" "${REST[@]}"
fi
