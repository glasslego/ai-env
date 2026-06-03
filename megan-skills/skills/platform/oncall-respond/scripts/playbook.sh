#!/usr/bin/env bash
# oncall-respond — cde-skills/operations/oncall/references/guide.md 검색 헬퍼.

set -euo pipefail

LIST_ONLY=0
QUERY=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --list) LIST_ONLY=1; shift;;
        -h|--help) sed -n '2,15p' "$0"; exit 0;;
        *) QUERY+="${QUERY:+ }$1"; shift;;
    esac
done

# guide.md 위치 후보
PATHS=(
    "${HOME}/.claude/skills/operations/oncall/references/guide.md"
    "${HOME}/work/glasslego/ai-env/cde-skills/skills/operations/oncall/references/guide.md"
)
GUIDE=""
for p in "${PATHS[@]}"; do [[ -f "$p" ]] && GUIDE="$p" && break; done
[[ -z "$GUIDE" ]] && { echo "❌ oncall guide.md not found. ai-env sync 후 재시도." >&2; exit 2; }

if [[ $LIST_ONLY -eq 1 ]]; then
    echo "# 온콜 플레이북 카테고리 (from $GUIDE)"
    echo
    grep -E '^## [0-9]+\.' "$GUIDE"
    echo
    echo "  → 키워드 검색: $0 \"<keyword>\""
    exit 0
fi

if [[ -z "$QUERY" ]]; then
    echo "usage: playbook.sh [--list] | <keyword>" >&2
    exit 2
fi

# 키워드 ↔ 매칭 섹션 (### 헤더 + 다음 ## 또는 ### 까지)
echo "# 매칭 플레이북: '$QUERY'"
echo
awk -v q="$QUERY" '
    BEGIN { IGNORECASE=1; in_match=0 }
    /^## / { in_match=0 }
    /^### / {
        in_match=0
        # 새 섹션 헤더가 키워드 매칭이면 출력 시작
        if (index(tolower($0), tolower(q))) { in_match=1; print; next }
    }
    /^## [0-9]+\./ {
        # 섹션 헤더 자체가 매칭되면 다음 ### 까지 출력
        if (index(tolower($0), tolower(q))) { in_match=1; print; next }
    }
    in_match { print }
' "$GUIDE"

echo
echo "---"
echo "더 자세히: less '$GUIDE' 또는 사용자 vault 의 _meta/oncall-cheatsheet.md"
