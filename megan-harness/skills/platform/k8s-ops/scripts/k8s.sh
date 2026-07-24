#!/usr/bin/env bash
# k8s-ops — cde-skills/platform/kubernetes 위임 (read-mostly).

set -euo pipefail

NEW=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help) sed -n '2,20p' "$0"; exit 0;;
        delete|apply|exec|edit|patch|scale)
            echo "❌ mutating 명령 '$1' 차단됨. cde-skills 직접 호출 + --confirm." >&2
            exit 2;;
        *) NEW+=("$1"); shift;;
    esac
done

[[ ${#NEW[@]} -eq 0 ]] && {
    echo "usage: k8s.sh <contexts|pods|logs|observe|metrics|cp> [args]" >&2
    exit 2
}

SUB="${NEW[0]}"; REST=("${NEW[@]:1}")
case "$SUB" in
    contexts) MODULE="k8s_context"; CMD="list";;
    pods) MODULE="k8s_pod"; CMD="list";;
    logs) MODULE="k8s_pod"; CMD="logs";;
    observe) MODULE="k8s_observe"; CMD="run";;
    metrics) MODULE="k8s_metrics"; CMD="show";;
    cp) MODULE="k8s_copy"; CMD="copy";;
    *) echo "unknown subcommand: $SUB" >&2; exit 2;;
esac

# cp 인자 검사: pod→local 만 허용 (local→pod 차단)
if [[ "$SUB" == "cp" && ${#REST[@]} -ge 2 ]]; then
    SRC="${REST[-2]}"; DST="${REST[-1]}"
    # pod 경로는 NAMESPACE/POD:/path 또는 POD:/path 형태로 가정
    if [[ "$SRC" != *":"* && "$DST" == *":"* ]]; then
        echo "❌ local→pod 방향 cp 차단됨 (read 방향만 허용)." >&2
        exit 2
    fi
fi

PATHS=(
    "${HOME}/.claude/skills/platform/kubernetes/scripts/${MODULE}.py"
    "${HOME}/work/glasslego/ai-env/cde-skills/skills/platform/kubernetes/scripts/${MODULE}.py"
)
DELEGATE=""
for p in "${PATHS[@]}"; do [[ -f "$p" ]] && DELEGATE="$p" && break; done
[[ -z "$DELEGATE" ]] && { echo "❌ ${MODULE}.py not found." >&2; exit 2; }

exec uv run python "$DELEGATE" "$CMD" "${REST[@]}"
