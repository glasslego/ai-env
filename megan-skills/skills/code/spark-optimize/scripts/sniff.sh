#!/usr/bin/env bash
# Spark anti-pattern sniff. 결정적 grep — 자동 수정 안 함.

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "usage: sniff.sh <file-or-dir>" >&2
    exit 2
fi
TARGET="$1"
[[ ! -e "$TARGET" ]] && { echo "not found: $TARGET" >&2; exit 2; }

scan() {
    local pattern="$1" label="$2" suggest="$3"
    local result
    result="$(grep -rEn --include='*.py' "$pattern" "$TARGET" 2>/dev/null || true)"
    if [[ -n "$result" ]]; then
        echo "## ${label}"
        echo "권장: ${suggest}"
        echo '```'
        echo "$result"
        echo '```'
        echo
    fi
}

echo "# Spark Anti-pattern Sniff — ${TARGET}"
echo

scan '@udf|\budf\(' \
    "UDF 사용" \
    "네이티브 F.<func> 로 가능한지 먼저 확인. 불가피하면 pandas_udf 우선."

scan 'from pyspark\.sql\.functions import \*' \
    "import *" \
    "from pyspark.sql import functions as F (전역 F alias 컨벤션)."

scan '\.collect\(\)' \
    "collect() 호출" \
    "결과가 driver 메모리에 적재됨. 큰 DF 면 .write 또는 .toLocalIterator()."

scan '\.toPandas\(\)' \
    "toPandas()" \
    "분산 collect — 큰 DF 위험. arrow 활성화 + 사이즈 limit."

scan '\.repartition\(\s*[0-9]+\s*\)' \
    "repartition 고정값" \
    "데이터 규모 대비 합리성 검토. spark.sql.shuffle.partitions 와 정렬."

# cache/unpersist 짝 검사
CACHE_FILES=$(grep -rEln --include='*.py' '\.(cache|persist)\(' "$TARGET" 2>/dev/null || true)
if [[ -n "$CACHE_FILES" ]]; then
    echo "## cache/persist 사용 — unpersist 짝 확인"
    echo "권장: cache() 사용 시 .unpersist() 쌍 보장."
    echo '```'
    while IFS= read -r f; do
        c=$(grep -cE '\.(cache|persist)\(' "$f" || echo 0)
        u=$(grep -cE '\.unpersist\(' "$f" || echo 0)
        echo "$f — cache/persist:${c} unpersist:${u}"
    done <<< "$CACHE_FILES"
    echo '```'
    echo
fi

# join 근처 broadcast 단서 (정확도 낮음 — 단순 grep)
JOIN_NO_BC=$(grep -rEln --include='*.py' '\.join\(' "$TARGET" 2>/dev/null | xargs -I{} grep -L 'broadcast' {} 2>/dev/null || true)
if [[ -n "$JOIN_NO_BC" ]]; then
    echo "## join 사용 + broadcast 미사용"
    echo "권장: 작은 dim 테이블 join 시 broadcast() 적용 검토."
    echo '```'
    echo "$JOIN_NO_BC"
    echo '```'
    echo
fi

echo "---"
echo "이 결과는 정적 sniff. 수정안은 in-conversation 으로 Claude/Codex 가 라인별로 제시."
