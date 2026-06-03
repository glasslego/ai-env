#!/usr/bin/env bash
# airflow-ops — cde-skills/orchestration/airflow 위임 wrapper.
# Read + trigger + pause 만 노출 (delete 류는 차단).

set -euo pipefail

ENV="${AIRFLOW_DEFAULT_ENV:-prod}"
SAVE_SLUG=""
SAVE=0

# --env / --save 는 wrapper 가 흡수, 그 외는 cde-skills 로 전달
ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --env) ENV="$2"; shift 2;;
        --save) SAVE=1; SAVE_SLUG="$2"; shift 2;;
        -h|--help) sed -n '2,30p' "$0"; exit 0;;
        delete|delete-run|update-state)
            echo "❌ 파괴적 명령 '$1' 는 본 wrapper 에서 차단됨." >&2
            echo "   필요시 cde-skills 서브스킬을 직접 호출하세요." >&2
            exit 2;;
        *) ARGS+=("$1"); shift;;
    esac
done

if [[ ${#ARGS[@]} -eq 0 ]]; then
    echo "usage: airflow.sh [--env ENV] [--save SLUG] <subcommand> [args...]" >&2
    echo "subcommands (DAG): list | details DAG | runs DAG | trigger DAG | pause DAG | unpause DAG" >&2
    echo "subcommands (Task): task DAG TASK | task-list DAG" >&2
    exit 2
fi

SUB="${ARGS[0]}"
REST=("${ARGS[@]:1}")

# DAG vs Task 라우팅 — 명령 prefix 로 판단
case "$SUB" in
    task|task-list) MODULE="airflow_task";;
    *) MODULE="airflow_dag";;
esac

# cde-skills 위임 스크립트 경로 후보
PATHS=(
    "${HOME}/.claude/skills/orchestration/airflow/scripts/${MODULE}.py"
    "${HOME}/.claude/skills/cde-skills/skills/orchestration/airflow/scripts/${MODULE}.py"
    "${HOME}/work/glasslego/ai-env/cde-skills/skills/orchestration/airflow/scripts/${MODULE}.py"
)
DELEGATE=""
for p in "${PATHS[@]}"; do
    [[ -f "$p" ]] && DELEGATE="$p" && break
done

if [[ -z "$DELEGATE" ]]; then
    echo "❌ ${MODULE}.py not found. ai-env sync 후 재시도." >&2
    exit 2
fi

# 결과 캡처용
TMP_OUT=""
if [[ $SAVE -eq 1 ]]; then
    TMP_OUT=$(mktemp -t airflow-out.XXXXXX)
    trap 'rm -f "$TMP_OUT"' EXIT
fi

# 실제 실행
if [[ $SAVE -eq 1 ]]; then
    uv run python "$DELEGATE" --env "$ENV" "$SUB" "${REST[@]}" 2>&1 | tee "$TMP_OUT"
else
    exec uv run python "$DELEGATE" --env "$ENV" "$SUB" "${REST[@]}"
fi

# 옵시디언 저장
if [[ $SAVE -eq 1 && -s "$TMP_OUT" ]]; then
    VAULT="${OBSIDIAN_BASE:-${HOME}/Documents/Obsidian Vault}"
    DATE=$(date '+%Y-%m-%d')
    MONTH=$(date '+%Y-%m')
    DIR="${VAULT}/90_journal/04_sessions/${MONTH}"
    mkdir -p "$DIR"
    NOTE="${DIR}/${DATE}-${SAVE_SLUG}-airflow.md"
    {
        echo "---"
        echo "date: ${DATE}"
        echo "type: ops"
        echo "platform: airflow"
        echo "tags: [airflow, ops]"
        echo "---"
        echo
        echo "# Airflow ${SUB} — ${REST[*]:-} (env=${ENV})"
        echo
        echo '```'
        cat "$TMP_OUT"
        echo '```'
    } > "$NOTE"
    echo "💾 saved: $NOTE" >&2
fi
