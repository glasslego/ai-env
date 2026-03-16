#!/usr/bin/env bash
# session_start.sh — SessionStart hook
# 1) 팀 스킬 git pull + 동기화 (백그라운드)
# 2) .claude/handoff/latest.md 로드 (프로젝트 로컬 — 우선)
# 3) ai-agent-log 이전 세션 요약 로드 (fallback)
# Hook event: SessionStart (matcher: "startup|resume")

set -euo pipefail

# 팀 스킬 git pull + 동기화 (백그라운드, 출력 완전 차단)
AI_ENV_DIR="${HOME}/work/glasslego/ai-env"
if [[ -d "$AI_ENV_DIR" ]]; then
    (
        # Claude UI PTY와 완전히 분리:
        # 1) exec로 stdin/stdout/stderr를 /dev/null로
        # 2) TERM=dumb으로 Rich/uv의 터미널 제어 시퀀스 차단
        # 3) NO_COLOR=1로 색상 출력 비활성화
        # 4) UV_NO_PROGRESS=1로 uv progress bar 차단
        export TERM=dumb NO_COLOR=1 UV_NO_PROGRESS=1
        exec </dev/null >/dev/null 2>&1
        cd "$AI_ENV_DIR"
        unset VIRTUAL_ENV
        # cde-*skills 디렉토리 git pull (fast-forward only)
        # nullglob: 매칭 없으면 빈 배열 (zsh no-match 에러 방지)
        setopt nullglob 2>/dev/null || shopt -s nullglob 2>/dev/null || true
        for d in cde-*skills; do
            [[ -d "$d/.git" ]] && git -C "$d" pull --ff-only --quiet 2>/dev/null || true
        done
        # 전체 팀 스킬 동기화
        uv run ai-env sync --skills-only --skills-all </dev/null >/dev/null 2>&1
    ) &
    # 서브쉘 disown으로 TTY 시그널 완전 분리
    disown 2>/dev/null || true
fi

# --- 0) .claude/logs/ 오래된 로그 정리 (7일 이상) ---
LOGS_DIR=".claude/logs"
if [[ -d "$LOGS_DIR" ]]; then
    find "$LOGS_DIR" -type f \( -name "*.log" -o -name "*.md" \) -mtime +7 -delete 2>/dev/null || true
fi

# 현재 프로젝트 루트
PROJECT_ROOT=""
if git rev-parse --show-toplevel &>/dev/null; then
    PROJECT_ROOT="$(git rev-parse --show-toplevel)"
    PROJECT_NAME="$(basename "$PROJECT_ROOT")"
else
    PROJECT_ROOT="$PWD"
    PROJECT_NAME="$(basename "$PWD")"
fi

# --- 1) .claude/handoff/latest.md 로드 (우선) ---
HANDOFF_FILE="${PROJECT_ROOT}/.claude/handoff/latest.md"
HANDOFF_LOADED=false

if [[ -f "$HANDOFF_FILE" ]]; then
    echo "## Previous Session Handoff (${PROJECT_NAME})"
    echo ""
    cat "$HANDOFF_FILE"
    echo ""
    echo "---"
    echo "_Loaded from ${HANDOFF_FILE}_"
    HANDOFF_LOADED=true
fi

# --- 2) ai-agent-log fallback ---
if [[ "$HANDOFF_LOADED" = false ]]; then
    LOG_DIR="${HOME}/work/ai-agent-log/sessions"
    SUMMARY_FILE="${LOG_DIR}/${PROJECT_NAME}.summary.md"

    if [[ -f "$SUMMARY_FILE" ]]; then
        echo "## Previous Session Context (${PROJECT_NAME})"
        echo ""
        cat "$SUMMARY_FILE"
        echo ""
        echo "---"
        echo "_Loaded from ${SUMMARY_FILE}_"
    fi
fi
