#!/usr/bin/env bash
# github-pr — 현재 브랜치 변경사항으로 PR 생성.

set -euo pipefail

DRY_RUN=0
DRAFT=0
BASE=""
TITLE=""
BODY=""
BODY_FILE=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift;;
        --draft) DRAFT=1; shift;;
        --base) BASE="$2"; shift 2;;
        --title) TITLE="$2"; shift 2;;
        --body) BODY="$2"; shift 2;;
        --body-file) BODY_FILE="$2"; shift 2;;
        -h|--help) sed -n '2,30p' "$0"; exit 0;;
        *) echo "unknown arg: $1" >&2; exit 2;;
    esac
done

command -v gh >/dev/null || { echo "gh CLI not installed. brew install gh" >&2; exit 2; }

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "not a git repo" >&2; exit 2
fi

CUR="$(git rev-parse --abbrev-ref HEAD)"

# default branch detection
DEFAULT="$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|origin/||' || echo main)"

# base 결정
if [[ -z "$BASE" ]]; then
    if [[ "$CUR" != "develop" ]] && git show-ref --verify --quiet refs/heads/develop; then
        BASE="develop"
    else
        BASE="$DEFAULT"
    fi
fi

if [[ "$CUR" == "$BASE" || "$CUR" == "$DEFAULT" ]]; then
    echo "current branch ($CUR) == base ($BASE) — switch to a feature branch first." >&2
    exit 2
fi

# upstream 보장 (이미 push 되어 있으면 skip)
if ! git rev-parse --abbrev-ref "$CUR@{upstream}" >/dev/null 2>&1; then
    [[ $DRY_RUN -eq 0 ]] && git push -u origin "$CUR"
fi

# 제목 자동 도출
if [[ -z "$TITLE" ]]; then
    FIRST_COMMIT="$(git log "$BASE..HEAD" --reverse --format='%s' 2>/dev/null | head -1)"
    if [[ -z "$FIRST_COMMIT" ]]; then
        echo "no commits between $BASE..$CUR" >&2; exit 2
    fi
    TICKET="$(echo "$CUR" | grep -oE 'CDE-[0-9]+' | head -1 || true)"
    if [[ -n "$TICKET" && "$FIRST_COMMIT" != *"$TICKET"* ]]; then
        TITLE="[$TICKET] $FIRST_COMMIT"
    else
        TITLE="$FIRST_COMMIT"
    fi
    # 70자 cut
    TITLE="$(echo "$TITLE" | cut -c1-70)"
fi

# 본문 결정
if [[ -n "$BODY_FILE" ]]; then
    [[ -f "$BODY_FILE" ]] || { echo "body file not found: $BODY_FILE" >&2; exit 2; }
    BODY="$(cat "$BODY_FILE")"
elif [[ -z "$BODY" ]]; then
    SUMMARY="$(git log "$BASE..HEAD" --reverse --format='- %s' 2>/dev/null)"
    # 테스트 명령 추론
    TEST_HINT="manual smoke test"
    if [[ -f pyproject.toml ]] && grep -q pytest pyproject.toml; then
        TEST_HINT="uv run pytest"
    elif [[ -f package.json ]] && grep -q '"test"' package.json; then
        TEST_HINT="npm test"
    fi
    BODY="$(cat <<EOF
## Summary
${SUMMARY}

## Test plan
- [ ] ${TEST_HINT}
- [ ] manual smoke test

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
fi

echo "base    : $BASE"
echo "branch  : $CUR"
echo "title   : $TITLE"
echo "---body---"
echo "$BODY"
echo "----------"

if [[ $DRY_RUN -eq 1 ]]; then
    echo "(dry-run) — not creating PR."
    exit 0
fi

CMD=(gh pr create --base "$BASE" --title "$TITLE" --body "$BODY")
[[ $DRAFT -eq 1 ]] && CMD+=(--draft)

"${CMD[@]}"
