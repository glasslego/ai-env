#!/usr/bin/env bash
# git-branch — 표준 네이밍으로 새 브랜치 생성.

set -euo pipefail

DRY_RUN=0
BASE=""
INPUT=""
PUSH=${BRANCH_TRACK_ORIGIN:-0}
TICKET_PATTERN="${BRANCH_TICKET_PATTERN:-CDE-[0-9]+}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run) DRY_RUN=1; shift;;
        --base) BASE="$2"; shift 2;;
        --push) PUSH=1; shift;;
        -h|--help) sed -n '2,30p' "$0"; exit 0;;
        *) INPUT+="${INPUT:+ }$1"; shift;;
    esac
done

if [[ -z "$INPUT" ]]; then
    echo "usage: create.sh [--base BR] [--dry-run] [--push] '<ticket-or-summary>'" >&2
    exit 2
fi

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

# prefix 추론 — 첫 번째 매칭 키워드만 prefix 로 흡수, 나머지는 slug 에 남긴다.
LOWER="$(echo "$INPUT" | tr '[:upper:]' '[:lower:]')"
PREFIX="feat"
PREFIX_KW=""  # slug 에서 제거할 단어 (prefix 로 매칭된 그것만)
for kw in fix bug oom crash chore docs refactor test feat feature; do
    case " $LOWER " in
        *" $kw "*)
            case "$kw" in
                fix|bug|oom|crash) PREFIX="fix";;
                feature)           PREFIX="feat";;
                *)                 PREFIX="$kw";;
            esac
            PREFIX_KW="$kw"
            break;;
    esac
done

# CDE 티켓 추출 (대문자 유지)
TICKET="$(echo "$INPUT" | grep -oE "$TICKET_PATTERN" | head -1 || true)"

# slug: ticket 제거 + prefix 로 매칭된 단어만 제거 → 소문자 → 비영숫자→`-`
SLUG="$(echo "$INPUT" | sed -E "s/$TICKET_PATTERN//g" | tr '[:upper:]' '[:lower:]')"
if [[ -n "$PREFIX_KW" ]]; then
    SLUG="$(echo "$SLUG" | awk -v kw="$PREFIX_KW" '{
        out=""
        skipped=0
        for (i=1;i<=NF;i++) {
            if (!skipped && $i == kw) { skipped=1; continue }
            out = out (out==""?"":" ") $i
        }
        print out
    }')"
fi
SLUG="$(echo "$SLUG" | sed -E 's/[^a-z0-9]+/-/g; s/^-+|-+$//g')"

# 최종 브랜치명
PARTS=()
[[ -n "$TICKET" ]] && PARTS+=("$TICKET")
[[ -n "$SLUG" ]] && PARTS+=("$SLUG")
NAME="$PREFIX/$(IFS=-; echo "${PARTS[*]}")"
NAME="${NAME%-}"  # trailing dash

if [[ "$NAME" == "$PREFIX/" ]]; then
    echo "could not derive a usable branch name from input: '$INPUT'" >&2
    exit 2
fi

echo "base   : $BASE"
echo "branch : $NAME"

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
