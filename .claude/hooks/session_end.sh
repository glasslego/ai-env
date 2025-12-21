#!/usr/bin/env bash
# session_end.sh — SessionEnd hook
# 세션 종료 시:
# 1) git 상태 + 마지막 사용자 메시지 기반 요약을 ai-agent-log에 저장
# 2) .claude/handoff/에 기본 컨텍스트 저장 (Claude가 /handoff로 풍부한 버전을 작성하지 않았을 경우 fallback)
# Hook event: SessionEnd
# stdin: JSON with session_id, transcript_path, etc.

set -euo pipefail

LOG_DIR="${HOME}/work/ai-agent-log/sessions"
mkdir -p "$LOG_DIR"

# 현재 프로젝트 이름 추출
PROJECT_ROOT=""
if git rev-parse --show-toplevel &>/dev/null; then
    PROJECT_ROOT="$(git rev-parse --show-toplevel)"
    PROJECT_NAME="$(basename "$PROJECT_ROOT")"
else
    PROJECT_ROOT="$PWD"
    PROJECT_NAME="$(basename "$PWD")"
fi

SUMMARY_FILE="${LOG_DIR}/${PROJECT_NAME}.summary.md"

# stdin에서 세션 정보 읽기
INPUT="$(cat)"
SESSION_ID="$(echo "$INPUT" | grep -o '"session_id":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "unknown")"
TRANSCRIPT_PATH="$(echo "$INPUT" | grep -o '"transcript_path":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")"

# git 상태 수집 (실패해도 계속 진행)
GIT_BRANCH="$(git branch --show-current 2>/dev/null || echo "N/A")"
GIT_LOG="$(git log --oneline -5 2>/dev/null || echo "N/A")"
GIT_STATUS="$(git status --short 2>/dev/null || echo "N/A")"
GIT_DIFF_STAT="$(git diff --stat 2>/dev/null || echo "N/A")"

# 마지막 사용자 메시지 추출 (transcript에서 규칙 기반)
LAST_USER_MSG=""
if [[ -n "$TRANSCRIPT_PATH" && -f "$TRANSCRIPT_PATH" ]]; then
    LAST_USER_MSG="$(grep -o '"type":"human"' "$TRANSCRIPT_PATH" >/dev/null 2>&1 && \
        grep '"type":"human"' "$TRANSCRIPT_PATH" | tail -1 | \
        grep -o '"text":"[^"]*"' | head -1 | cut -d'"' -f4 | head -c 200 || echo "")"
fi

TIMESTAMP="$(date '+%Y-%m-%d %H:%M')"
SHORT_ID="${SESSION_ID:0:8}"

# --- 1) ai-agent-log 요약 파일 ---
cat > "$SUMMARY_FILE" << EOF
# Session Summary: ${PROJECT_NAME}

- **Date**: ${TIMESTAMP}
- **Session ID**: ${SESSION_ID}
- **Branch**: ${GIT_BRANCH}

## Recent Commits
\`\`\`
${GIT_LOG}
\`\`\`

## Working Tree Status
\`\`\`
${GIT_STATUS}
\`\`\`

## Changed Files
\`\`\`
${GIT_DIFF_STAT}
\`\`\`

## Last Task
${LAST_USER_MSG:-"(no user message extracted)"}
EOF

# --- 2) .claude/handoff/ fallback ---
HANDOFF_DIR="${PROJECT_ROOT}/.claude/handoff"
ARCHIVE_DIR="${HANDOFF_DIR}/archive"
LATEST="${HANDOFF_DIR}/latest.md"

mkdir -p "$ARCHIVE_DIR"

# 기존 latest.md가 있으면 archive로 이동
if [[ -f "$LATEST" ]]; then
    # latest.md의 Date 줄에서 날짜 추출, 없으면 현재 시간 사용
    PREV_DATE="$(grep -m1 '^- Date:' "$LATEST" | sed 's/.*: //' | tr ' :' '_' || echo "")"
    PREV_ID="$(grep -m1 '^- Session:' "$LATEST" | sed 's/.*: //' || echo "unknown")"
    ARCHIVE_NAME="${PREV_DATE:-$(date '+%Y%m%d_%H%M')}_${PREV_ID:0:8}.md"
    mv "$LATEST" "${ARCHIVE_DIR}/${ARCHIVE_NAME}" 2>/dev/null || true

    # archive에 10개 초과 시 오래된 것 삭제
    ARCHIVE_COUNT="$(ls -1 "$ARCHIVE_DIR"/*.md 2>/dev/null | wc -l | tr -d ' ')"
    if [[ "$ARCHIVE_COUNT" -gt 10 ]]; then
        ls -1t "$ARCHIVE_DIR"/*.md | tail -n +"11" | xargs rm -f 2>/dev/null || true
    fi
fi

# Claude가 이미 /handoff로 풍부한 latest.md를 작성했을 수 있으므로
# 여기서는 latest.md가 없을 때만 fallback으로 기본 정보 작성
if [[ ! -f "$LATEST" ]]; then
    cat > "$LATEST" << EOF
# Handoff: ${PROJECT_NAME}
- Date: ${TIMESTAMP}
- Session: ${SHORT_ID}
- Branch: ${GIT_BRANCH}

## 진행 중이던 작업
${LAST_USER_MSG:-"(세션 컨텍스트 자동 추출 실패 — /handoff 커맨드로 직접 작성 권장)"}

## 다음 해야 할 것
(자동 생성 — 상세 내용은 다음 세션에서 확인)

## 변경된 파일
\`\`\`
${GIT_DIFF_STAT}
\`\`\`

## Recent Commits
\`\`\`
${GIT_LOG}
\`\`\`
EOF
fi
