#!/usr/bin/env bash
# Branch guard — 위험한 git push 차단.

set -euo pipefail

PROTECTED_DEFAULT="main,master,develop"
PROTECTED="${BRANCH_GUARD_PROTECTED:-$PROTECTED_DEFAULT}"
TARGET=""
FORCE=0
ACTION="check"

while [[ $# -gt 0 ]]; do
    case "$1" in
        check) ACTION="check"; shift;;
        --target) TARGET="$2"; shift 2;;
        --force) FORCE=1; shift;;
        -h|--help) sed -n '2,30p' "$0"; exit 0;;
        *) echo "unknown arg: $1" >&2; exit 2;;
    esac
done

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "git 레포 아님." >&2
    exit 2
fi

CUR="$(git rev-parse --abbrev-ref HEAD)"
[[ -z "$TARGET" ]] && TARGET="$CUR"

is_protected() {
    local b="$1"
    IFS=',' read -ra arr <<< "$PROTECTED"
    for p in "${arr[@]}"; do
        [[ "$b" == "$p" ]] && return 0
    done
    return 1
}

ERRORS=()
WARNINGS=()

if is_protected "$TARGET"; then
    if [[ "${BRANCH_GUARD_OVERRIDE:-0}" != "1" ]]; then
        ERRORS+=("protected branch direct push: target='${TARGET}' — 의도적이면 BRANCH_GUARD_OVERRIDE=1 로 우회")
    else
        WARNINGS+=("protected branch direct push 우회됨 (BRANCH_GUARD_OVERRIDE=1)")
    fi
fi

if [[ "$FORCE" == 1 ]] && is_protected "$TARGET"; then
    if [[ "${BRANCH_GUARD_OVERRIDE:-0}" != "1" ]]; then
        ERRORS+=("force push to protected branch: target='${TARGET}'")
    fi
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
    WARNINGS+=("dirty tree: uncommitted 변경 있음 — push 전 commit/stash 검토")
fi

UPSTREAM="origin/${TARGET}"
if git rev-parse --verify "$UPSTREAM" >/dev/null 2>&1; then
    BEHIND="$(git rev-list --count "HEAD..${UPSTREAM}" 2>/dev/null || echo 0)"
    if (( BEHIND > 5 )); then
        WARNINGS+=("stale base: HEAD 가 ${UPSTREAM} 보다 ${BEHIND} 커밋 뒤처짐 — pull/rebase 검토")
    fi
fi

if (( ${#WARNINGS[@]} > 0 )); then
    printf '⚠️  %s\n' "${WARNINGS[@]}" >&2
fi
if (( ${#ERRORS[@]} > 0 )); then
    printf '❌ %s\n' "${ERRORS[@]}" >&2
    exit 1
fi
echo "ok: ${CUR} → ${TARGET}"
