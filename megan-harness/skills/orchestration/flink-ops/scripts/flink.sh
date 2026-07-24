#!/usr/bin/env bash
# flink-ops — cde-skills/orchestration/flink 위임 (read-only).

set -euo pipefail

ENV="${FLINK_DEFAULT_ENV:-prod}"
SAVE=0; SAVE_SLUG=""
NEW=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --env) ENV="$2"; shift 2;;
        --save) SAVE=1; SAVE_SLUG="$2"; shift 2;;
        -h|--help) sed -n '2,20p' "$0"; exit 0;;
        cancel|savepoint|restart|stop)
            echo "❌ mutating 명령 '$1' 차단됨 (read-only)." >&2; exit 2;;
        *) NEW+=("$1"); shift;;
    esac
done

[[ ${#NEW[@]} -eq 0 ]] && { echo "usage: flink.sh [--env ENV] <cluster|jobs|job-detail JID|job-exceptions JID>" >&2; exit 2; }

SUB="${NEW[0]}"; REST=("${NEW[@]:1}")
case "$SUB" in
    cluster) MODULE="flink_cluster"; CMD="info";;
    jobs) MODULE="flink_job"; CMD="list";;
    job-detail) MODULE="flink_job"; CMD="detail";;
    job-exceptions) MODULE="flink_job"; CMD="exceptions";;
    *) echo "unknown subcommand: $SUB" >&2; exit 2;;
esac

PATHS=(
    "${HOME}/.claude/skills/orchestration/flink/scripts/${MODULE}.py"
    "${HOME}/work/glasslego/ai-env/cde-skills/skills/orchestration/flink/scripts/${MODULE}.py"
)
DELEGATE=""
for p in "${PATHS[@]}"; do [[ -f "$p" ]] && DELEGATE="$p" && break; done
[[ -z "$DELEGATE" ]] && { echo "❌ ${MODULE}.py not found." >&2; exit 2; }

if [[ $SAVE -eq 1 ]]; then
    TMP_OUT=$(mktemp -t flink-out.XXXXXX); trap 'rm -f "$TMP_OUT"' EXIT
    uv run python "$DELEGATE" --env "$ENV" "$CMD" "${REST[@]}" 2>&1 | tee "$TMP_OUT"
    [[ -s "$TMP_OUT" ]] || exit 0
    VAULT="${OBSIDIAN_BASE:-${HOME}/Documents/Obsidian Vault}"
    DATE=$(date '+%Y-%m-%d'); MONTH=$(date '+%Y-%m')
    DIR="${VAULT}/90_journal/04_sessions/${MONTH}"; mkdir -p "$DIR"
    NOTE="${DIR}/${DATE}-${SAVE_SLUG}-flink.md"
    { echo "---"; echo "date: ${DATE}"; echo "type: ops"; echo "platform: flink"; echo "tags: [flink, ops]"; echo "---"; echo; echo "# Flink ${SUB} (env=${ENV})"; echo; echo '```'; cat "$TMP_OUT"; echo '```'; } > "$NOTE"
    echo "💾 saved: $NOTE" >&2
else
    exec uv run python "$DELEGATE" --env "$ENV" "$CMD" "${REST[@]}"
fi
