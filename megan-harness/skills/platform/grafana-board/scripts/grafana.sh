#!/usr/bin/env bash
# grafana-board — cde-skills/operations/grafana 위임 (read-only + open).

set -euo pipefail

ENV="${GRAFANA_DEFAULT_ENV:-prod}"
NEW=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --env) ENV="$2"; shift 2;;
        -h|--help) sed -n '2,15p' "$0"; exit 0;;
        import|sync|delete)
            echo "❌ mutating 명령 '$1' 차단됨." >&2; exit 2;;
        *) NEW+=("$1"); shift;;
    esac
done

[[ ${#NEW[@]} -eq 0 ]] && { echo "usage: grafana.sh [--env ENV] <list|search QUERY|open SLUG|export UID>" >&2; exit 2; }

SUB="${NEW[0]}"; REST=("${NEW[@]:1}")
case "$SUB" in
    list|search|open|export) CMD="$SUB";;
    *) echo "unknown subcommand: $SUB" >&2; exit 2;;
esac

PATHS=(
    "${HOME}/.claude/skills/operations/grafana/scripts/grafana_dashboard.py"
    "${HOME}/work/glasslego/ai-env/cde-skills/skills/operations/grafana/scripts/grafana_dashboard.py"
)
DELEGATE=""
for p in "${PATHS[@]}"; do [[ -f "$p" ]] && DELEGATE="$p" && break; done
[[ -z "$DELEGATE" ]] && { echo "❌ grafana_dashboard.py not found." >&2; exit 2; }

exec uv run python "$DELEGATE" --env "$ENV" "$CMD" "${REST[@]}"
