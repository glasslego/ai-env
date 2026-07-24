#!/usr/bin/env bash
# kdp-browse — cde-skills/data/kdp 위임 (read-only).

set -euo pipefail

SAVE=0; SAVE_SLUG=""
NEW=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --save) SAVE=1; SAVE_SLUG="$2"; shift 2;;
        -h|--help) sed -n '2,15p' "$0"; exit 0;;
        create|update|delete)
            echo "❌ mutating 명령 '$1' 차단됨 (read-only)." >&2; exit 2;;
        *) NEW+=("$1"); shift;;
    esac
done

[[ ${#NEW[@]} -eq 0 ]] && {
    echo "usage: kdp.sh <datasets|dataset ID|schema ID|columns ID|stats ID|permissions ID>" >&2
    exit 2
}

SUB="${NEW[0]}"; REST=("${NEW[@]:1}")
case "$SUB" in
    datasets)    MODULE="kdp_dataset";    CMD="list";;
    dataset)     MODULE="kdp_dataset";    CMD="get";;
    schema)      MODULE="kdp_schema";     CMD="get-columns";;
    columns)     MODULE="kdp_column";     CMD="list";;
    stats)       MODULE="kdp_statistics"; CMD="row-count";;
    eda)         MODULE="kdp_statistics"; CMD="eda";;
    permissions) MODULE="kdp_permission"; CMD="get-users";;
    *) echo "unknown subcommand: $SUB" >&2; exit 2;;
esac

PATHS=(
    "${HOME}/.claude/skills/data/kdp/scripts/${MODULE}.py"
    "${HOME}/work/glasslego/ai-env/cde-skills/skills/data/kdp/scripts/${MODULE}.py"
)
DELEGATE=""
for p in "${PATHS[@]}"; do [[ -f "$p" ]] && DELEGATE="$p" && break; done
[[ -z "$DELEGATE" ]] && { echo "❌ ${MODULE}.py not found." >&2; exit 2; }

if [[ $SAVE -eq 1 ]]; then
    TMP_OUT=$(mktemp -t kdp-out.XXXXXX); trap 'rm -f "$TMP_OUT"' EXIT
    uv run python "$DELEGATE" "$CMD" "${REST[@]}" 2>&1 | tee "$TMP_OUT"
    [[ -s "$TMP_OUT" ]] || exit 0
    VAULT="${OBSIDIAN_BASE:-${HOME}/Documents/Obsidian Vault}"
    DATE=$(date '+%Y-%m-%d'); MONTH=$(date '+%Y-%m')
    DIR="${VAULT}/90_journal/04_sessions/${MONTH}"; mkdir -p "$DIR"
    NOTE="${DIR}/${DATE}-${SAVE_SLUG}-kdp.md"
    { echo "---"; echo "date: ${DATE}"; echo "type: ops"; echo "platform: kdp"; echo "tags: [kdp, schema]"; echo "---"; echo; echo "# KDP ${SUB} ${REST[*]:-}"; echo; echo '```'; cat "$TMP_OUT"; echo '```'; } > "$NOTE"
    echo "💾 saved: $NOTE" >&2
else
    exec uv run python "$DELEGATE" "$CMD" "${REST[@]}"
fi
