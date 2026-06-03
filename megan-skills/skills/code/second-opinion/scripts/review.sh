#!/usr/bin/env bash
# git diff (HEAD vs base) → codex CLI 두 번째 의견.

set -euo pipefail

BASE=""
SAVE=0
MAX_BYTES=81920
VAULT="${OBSIDIAN_BASE:-${HOME}/Documents/Obsidian Vault}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --base) BASE="$2"; shift 2;;
        --save) SAVE=1; shift;;
        --max-bytes) MAX_BYTES="$2"; shift 2;;
        -h|--help) sed -n '2,15p' "$0"; exit 0;;
        *) echo "unknown arg: $1" >&2; exit 2;;
    esac
done

if ! command -v codex >/dev/null 2>&1; then
    echo "codex CLI 미설치. 설치 후 재시도." >&2
    exit 2
fi
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "현재 디렉토리가 git 레포가 아님." >&2
    exit 2
fi

if [[ -z "$BASE" ]]; then
    if git rev-parse --verify main >/dev/null 2>&1; then BASE=main
    elif git rev-parse --verify master >/dev/null 2>&1; then BASE=master
    else echo "main / master 모두 없음. --base 명시." >&2; exit 2
    fi
fi

MERGE_BASE="$(git merge-base HEAD "$BASE")"
DIFF="$(git diff "${MERGE_BASE}..HEAD")"
if [[ -z "$DIFF" ]]; then
    echo "변경사항 없음 (merge-base = HEAD)." >&2
    exit 0
fi

# 토큰 예산 컷오프
DIFF_BYTES="${#DIFF}"
if (( DIFF_BYTES > MAX_BYTES )); then
    DIFF="${DIFF:0:$MAX_BYTES}
... (diff 가 ${DIFF_BYTES} bytes 로 ${MAX_BYTES} 초과 — 잘림)"
fi

PROMPT="당신은 시니어 코드 리뷰어. 다음 git diff 에서 다음을 식별:
1. 명백한 버그 / 회귀 위험
2. 보안 위협 (입력 검증, 인증, secret 노출)
3. 테스트 누락
4. 명명/구조 개선 제안 (낮은 우선순위)

severity 별로 묶어 출력 (HIGH / MEDIUM / LOW). 한국어로 답변.

--- DIFF ---
${DIFF}"

TMP_OUT="$(mktemp)"
trap 'rm -f "$TMP_OUT"' EXIT

codex exec -c "approval_policy='never'" -s read-only "$PROMPT" > "$TMP_OUT" 2>&1 || {
    echo "codex 실행 실패." >&2
    cat "$TMP_OUT" >&2
    exit 1
}
cat "$TMP_OUT"

if [[ "$SAVE" == 1 ]]; then
    DATE_KST="$(TZ='Asia/Seoul' date +%Y-%m-%d)"
    HHMM="$(TZ='Asia/Seoul' date +%H%M)"
    YM="$(TZ='Asia/Seoul' date +%Y-%m)"
    NOTE_DIR="${VAULT}/90_journal/04_sessions/${YM}"
    mkdir -p "$NOTE_DIR"
    SHA="$(git rev-parse --short HEAD)"
    NOTE="${NOTE_DIR}/${DATE_KST}-${HHMM}-2nd-${SHA}.md"
    {
        echo "---"
        echo "date: ${DATE_KST}"
        echo "type: code-review"
        echo "tags: [second-opinion, codex]"
        echo "base: ${BASE}"
        echo "head: ${SHA}"
        echo "---"
        echo
        echo "# Second Opinion — ${SHA} vs ${BASE}"
        echo
        cat "$TMP_OUT"
    } > "$NOTE"
    echo "saved: $NOTE" >&2
fi
