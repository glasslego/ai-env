#!/usr/bin/env bash
# PR evaluator — diff 기반 결정적 sniff. 본격 평가는 in-conversation Claude/Codex.

set -euo pipefail

BASE=""
SAVE=0
WITH_SECOND=0
VAULT="${OBSIDIAN_BASE:-${HOME}/Documents/Obsidian Vault}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --base) BASE="$2"; shift 2;;
        --save) SAVE=1; shift;;
        --with-second) WITH_SECOND=1; shift;;
        -h|--help) sed -n '2,15p' "$0"; exit 0;;
        *) echo "unknown arg: $1" >&2; exit 2;;
    esac
done

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "git 레포 아님." >&2; exit 2
fi
if [[ -z "$BASE" ]]; then
    if git rev-parse --verify main >/dev/null 2>&1; then BASE=main
    elif git rev-parse --verify master >/dev/null 2>&1; then BASE=master
    else echo "main / master 없음." >&2; exit 2
    fi
fi

MERGE_BASE="$(git merge-base HEAD "$BASE")"

OUT="$(mktemp)"
trap 'rm -f "$OUT"' EXIT
{
    echo "# PR Evaluation — $(git rev-parse --short HEAD) vs ${BASE}"
    echo
    echo "## 변경 규모"
    echo '```'
    git diff "${MERGE_BASE}..HEAD" --stat
    echo '```'
    echo
    echo "## 결정적 sniff"
    echo
    echo "### 1) secret-like 패턴"
    if git diff "${MERGE_BASE}..HEAD" | grep -nE '^\+.*(password|token|secret|api_key|passwd)\s*=\s*["'"'"']' \
        | grep -v "_example\|\.template\|test_\|#"; then
        echo "  ⚠️  검출됨 — 위 라인 검토"
    else
        echo "  ✓ 검출 없음"
    fi
    echo
    echo "### 2) 새 TODO/FIXME"
    if git diff "${MERGE_BASE}..HEAD" | grep -nE '^\+.*(TODO|FIXME|XXX)'; then
        echo "  ⚠️  새 TODO 추가됨"
    else
        echo "  ✓ 추가 없음"
    fi
    echo
    echo "### 3) 의존성 변경"
    DEPS_FILES="pyproject.toml requirements.txt package.json package-lock.json uv.lock"
    DEP_CHANGED=0
    for f in $DEPS_FILES; do
        if git diff "${MERGE_BASE}..HEAD" -- "$f" | head -1 | grep -q .; then
            echo "  ⚠️  $f 변경됨"
            DEP_CHANGED=1
        fi
    done
    [[ "$DEP_CHANGED" == 0 ]] && echo "  ✓ 변경 없음"
    echo
    echo "### 4) 마이그레이션 / 스키마 변경"
    MIG_PATHS="migrations/ alembic/ *.sql"
    if git diff "${MERGE_BASE}..HEAD" --name-only | grep -E '(migrations/|alembic/|\.sql$)' >/dev/null; then
        echo "  ⚠️  검출됨 — rollback 안전성 확인"
        git diff "${MERGE_BASE}..HEAD" --name-only | grep -E '(migrations/|alembic/|\.sql$)' | sed 's/^/    - /'
    else
        echo "  ✓ 변경 없음"
    fi
    echo
    echo "### 5) 테스트 변경 비율"
    TOTAL_CHG=$(git diff "${MERGE_BASE}..HEAD" --shortstat | grep -oE '[0-9]+ files? changed' | grep -oE '[0-9]+' || echo 0)
    TEST_CHG=$(git diff "${MERGE_BASE}..HEAD" --name-only | grep -cE '(^tests?/|_test\.|test_|\.test\.)' || echo 0)
    echo "  test 파일: ${TEST_CHG} / 전체: ${TOTAL_CHG}"
    if [[ "$TOTAL_CHG" -gt 0 && "$TEST_CHG" == 0 ]]; then
        echo "  ⚠️  테스트 변경 없음 — 누락 검토"
    fi
    echo
    echo "## 7개 카테고리 in-conversation 평가 가이드"
    echo "  1. Spec 정합성, 2. 테스트, 3. 보안, 4. 성능, 5. 의존성, 6. 문서, 7. rollback 안전성"
    echo "  → 위 sniff 결과를 참고로 각 카테고리에 OK / WARN / BLOCK 판정."
} > "$OUT"
cat "$OUT"

if [[ "$WITH_SECOND" == 1 ]]; then
    echo
    echo "## Second Opinion (codex)"
    "$(dirname "$0")/../../second-opinion/scripts/review.sh" --base "$BASE" || true
fi

if [[ "$SAVE" == 1 ]]; then
    DATE_KST="$(TZ='Asia/Seoul' date +%Y-%m-%d)"
    HHMM="$(TZ='Asia/Seoul' date +%H%M)"
    YM="$(TZ='Asia/Seoul' date +%Y-%m)"
    SHA="$(git rev-parse --short HEAD)"
    NOTE_DIR="${VAULT}/90_journal/04_sessions/${YM}"
    mkdir -p "$NOTE_DIR"
    NOTE="${NOTE_DIR}/${DATE_KST}-${HHMM}-pr-eval-${SHA}.md"
    {
        echo "---"
        echo "date: ${DATE_KST}"
        echo "type: pr-eval"
        echo "tags: [pr, eval]"
        echo "base: ${BASE}"
        echo "head: ${SHA}"
        echo "---"
        echo
        cat "$OUT"
    } > "$NOTE"
    echo "saved: $NOTE" >&2
fi
