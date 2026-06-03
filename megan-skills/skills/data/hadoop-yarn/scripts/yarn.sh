#!/usr/bin/env bash
# hadoop-yarn — cde-skills/data/hadoop 위임 (read-only).

set -euo pipefail

SAVE=0; SAVE_SLUG=""
NEW=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --save) SAVE=1; SAVE_SLUG="$2"; shift 2;;
        -h|--help) sed -n '2,20p' "$0"; exit 0;;
        kill) echo "❌ kill 차단됨. cde-skills 서브스킬 + --confirm 사용." >&2; exit 2;;
        *) NEW+=("$1"); shift;;
    esac
done

[[ ${#NEW[@]} -eq 0 ]] && { echo "usage: yarn.sh <apps|app-detail APPID|nodes|queues> [extras]" >&2; exit 2; }

SUB="${NEW[0]}"; REST=("${NEW[@]:1}")
case "$SUB" in
    apps) MODULE="hadoop_application"; CMD="list";;
    app-detail) MODULE="hadoop_application"; CMD="detail";;
    nodes) MODULE="hadoop_node"; CMD="list";;
    queues) MODULE="hadoop_queue"; CMD="list";;
    *) echo "unknown subcommand: $SUB" >&2; exit 2;;
esac

PATHS=(
    "${HOME}/.claude/skills/data/hadoop/scripts/${MODULE}.py"
    "${HOME}/work/glasslego/ai-env/cde-skills/skills/data/hadoop/scripts/${MODULE}.py"
)
DELEGATE=""
for p in "${PATHS[@]}"; do [[ -f "$p" ]] && DELEGATE="$p" && break; done
[[ -z "$DELEGATE" ]] && { echo "❌ ${MODULE}.py not found." >&2; exit 2; }

if [[ $SAVE -eq 1 ]]; then
    TMP_OUT=$(mktemp -t yarn-out.XXXXXX); trap 'rm -f "$TMP_OUT"' EXIT
    uv run python "$DELEGATE" "$CMD" "${REST[@]}" 2>&1 | tee "$TMP_OUT"
    [[ -s "$TMP_OUT" ]] || exit 0
    VAULT="${OBSIDIAN_BASE:-${HOME}/Documents/Obsidian Vault}"
    DATE=$(date '+%Y-%m-%d'); MONTH=$(date '+%Y-%m')
    DIR="${VAULT}/90_journal/04_sessions/${MONTH}"; mkdir -p "$DIR"
    NOTE="${DIR}/${DATE}-${SAVE_SLUG}-yarn.md"
    { echo "---"; echo "date: ${DATE}"; echo "type: ops"; echo "platform: hadoop-yarn"; echo "tags: [hadoop, yarn, ops]"; echo "---"; echo; echo "# YARN ${SUB}"; echo; echo '```'; cat "$TMP_OUT"; echo '```'; } > "$NOTE"
    echo "💾 saved: $NOTE" >&2
else
    exec uv run python "$DELEGATE" "$CMD" "${REST[@]}"
fi
