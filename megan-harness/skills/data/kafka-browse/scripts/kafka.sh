#!/usr/bin/env bash
# kafka-browse — cde-skills/data/kafka 위임 (read-only).

set -euo pipefail

CLUSTER=""
SAVE=0
SAVE_SLUG=""

# 1패스: -c/--cluster, --save, 도움말
NEW=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        -c|--cluster) CLUSTER="$2"; shift 2;;
        --save) SAVE=1; SAVE_SLUG="$2"; shift 2;;
        -h|--help) sed -n '2,30p' "$0"; exit 0;;
        produce|delete|reset|alter)
            echo "❌ mutating 명령 '$1' 는 본 wrapper 에서 차단됨 (read-only)." >&2
            exit 2;;
        *) NEW+=("$1"); shift;;
    esac
done

if [[ ${#NEW[@]} -eq 0 ]]; then
    echo "usage: kafka.sh [-c CLUSTER] [--save SLUG] <subcommand> [args]" >&2
    echo "subcommands: clusters | topic-list | topic-describe -t TOPIC | consume -t TOPIC --max N" >&2
    exit 2
fi

SUB="${NEW[0]}"
REST=("${NEW[@]:1}")

# 모듈 라우팅
case "$SUB" in
    clusters) MODULE="kafka_cluster"; CMD="list";;
    topic-list) MODULE="kafka_topic"; CMD="list";;
    topic-describe) MODULE="kafka_topic"; CMD="describe";;
    consume) MODULE="kafka_consume"; CMD="run";;
    *) echo "unknown subcommand: $SUB" >&2; exit 2;;
esac

PATHS=(
    "${HOME}/.claude/skills/data/kafka/scripts/${MODULE}.py"
    "${HOME}/.claude/skills/cde-skills/skills/data/kafka/scripts/${MODULE}.py"
    "${HOME}/work/glasslego/ai-env/cde-skills/skills/data/kafka/scripts/${MODULE}.py"
)
DELEGATE=""
for p in "${PATHS[@]}"; do
    [[ -f "$p" ]] && DELEGATE="$p" && break
done

if [[ -z "$DELEGATE" ]]; then
    echo "❌ ${MODULE}.py not found. ai-env sync 후 재시도." >&2
    exit 2
fi

# clusters 명령은 -c 없이 가능, 그 외는 -c 필수
if [[ "$SUB" != "clusters" && -z "$CLUSTER" ]]; then
    echo "❌ -c CLUSTER 필요 (clusters 로 목록 확인)." >&2
    exit 2
fi

ARGS=()
[[ -n "$CLUSTER" ]] && ARGS+=("-c" "$CLUSTER")
ARGS+=("$CMD" "${REST[@]}")

# 실행
if [[ $SAVE -eq 1 ]]; then
    TMP_OUT=$(mktemp -t kafka-out.XXXXXX)
    trap 'rm -f "$TMP_OUT"' EXIT
    uv run python "$DELEGATE" "${ARGS[@]}" 2>&1 | tee "$TMP_OUT"
    if [[ -s "$TMP_OUT" ]]; then
        VAULT="${OBSIDIAN_BASE:-${HOME}/Documents/Obsidian Vault}"
        DATE=$(date '+%Y-%m-%d')
        MONTH=$(date '+%Y-%m')
        DIR="${VAULT}/90_journal/04_sessions/${MONTH}"
        mkdir -p "$DIR"
        NOTE="${DIR}/${DATE}-${SAVE_SLUG}-kafka.md"
        {
            echo "---"
            echo "date: ${DATE}"
            echo "type: ops"
            echo "platform: kafka"
            echo "tags: [kafka, ops]"
            echo "---"
            echo
            echo "# Kafka ${SUB} — cluster=${CLUSTER:-(n/a)}"
            echo
            echo '```'
            cat "$TMP_OUT"
            echo '```'
        } > "$NOTE"
        echo "💾 saved: $NOTE" >&2
    fi
else
    exec uv run python "$DELEGATE" "${ARGS[@]}"
fi
