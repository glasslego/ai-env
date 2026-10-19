#!/usr/bin/env bash
# git-branch — 표준 네이밍으로 새 브랜치 생성.
#
# 규칙:
#   - Jira 작업     → Jira 키 그대로 (예: CDETEAM-1234)
#   - Jira 없는 작업 → CDETEAM-NOJIRA-YYYYMMDDHH (생성 시각)
#   - codex/claude 등 에이전트 이름, feat/ 같은 prefix, 요약 slug 를 붙이지 않는다.
#
# usage: create.sh [--base BR] [--dry-run] [--push] ['<CDETEAM-XXXX 또는 아무 텍스트>']

set -euo pipefail

DRY_RUN=0
BASE=""
INPUT=""
PUSH=${BRANCH_TRACK_ORIGIN:-0}
TICKET_PATTERN="${BRANCH_TICKET_PATTERN:-CDETEAM-[0-9]+}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift;;
        --base) BASE="$2"; shift 2;;
        --push) PUSH=1; shift;;
        -h|--help) sed -n '2,9p' "$0"; exit 0;;
        *) INPUT+="${INPUT:+ }$1"; shift;;
    esac
done

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "not a git repo" >&2; exit 2
fi

# dirty tree 경고
if [[ -n "$(git status --porcelain)" ]]; then
    echo "WARN: dirty working tree — commit or stash before creating new branch." >&2
fi

# base 결정: --base > develop > main > origin/HEAD
if [[ -z "$BASE" ]]; then
    if git show-ref --verify --quiet refs/heads/develop; then
        BASE="develop"
    elif git show-ref --verify --quiet refs/heads/main; then
        BASE="main"
    else
        BASE="$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|origin/||' || echo main)"
    fi
fi

# 브랜치명: Jira 키가 있으면 그대로, 없으면 NOJIRA + 생성 시각
TICKET="$(echo "$INPUT" | grep -oE "$TICKET_PATTERN" | head -1 || true)"
if [[ -n "$TICKET" ]]; then
    NAME="$TICKET"
else
    NAME="CDETEAM-NOJIRA-$(date +%Y%m%d%H)"
fi

echo "base   : $BASE"
echo "branch : $NAME"

if git show-ref --verify --quiet "refs/heads/$NAME"; then
    echo "branch already exists: $NAME" >&2; exit 2
fi

if [[ $DRY_RUN -eq 1 ]]; then
    echo "(dry-run) — not creating."
    exit 0
fi

git fetch origin "$BASE" --quiet 2>/dev/null || true
git checkout "$BASE"
git pull --ff-only --quiet 2>/dev/null || true
git checkout -b "$NAME"

if [[ $PUSH -eq 1 ]]; then
    git push -u origin "$NAME"
fi

echo "created: $NAME (from $BASE)"
