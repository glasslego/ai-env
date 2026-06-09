#!/usr/bin/env bash
# pre_compact.sh — PreCompact hook (async: true)
# 1) compact 전 transcript를 백업 디렉토리에 복사
# 2) handoff/latest.md가 없으면 기본 정보로 생성 (compact으로 컨텍스트 손실 대비)
# 3) Obsidian 00_session에 압축 세션 스냅샷 저장
# Hook event: PreCompact

set -euo pipefail

BACKUP_DIR="${HOME}/work/ai-agent-log/transcripts"
mkdir -p "$BACKUP_DIR"

# 현재 프로젝트
PROJECT_ROOT=""
if git rev-parse --show-toplevel &>/dev/null; then
    PROJECT_ROOT="$(git rev-parse --show-toplevel)"
    PROJECT_NAME="$(basename "$PROJECT_ROOT")"
else
    PROJECT_ROOT="$PWD"
    PROJECT_NAME="$(basename "$PWD")"
fi

# stdin에서 transcript 경로 추출
INPUT="$(cat)"
TRANSCRIPT_PATH="$(echo "$INPUT" | grep -o '"transcript_path":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "")"
SESSION_ID="$(echo "$INPUT" | grep -o '"session_id":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "unknown")"

TIMESTAMP="$(date '+%Y%m%d_%H%M')"
SHORT_ID="${SESSION_ID:0:8}"

# --- 1) Transcript 백업 ---
if [[ -n "$TRANSCRIPT_PATH" && -f "$TRANSCRIPT_PATH" ]]; then
    BACKUP_FILE="${BACKUP_DIR}/${PROJECT_NAME}__${SHORT_ID}__${TIMESTAMP}.jsonl"
    cp "$TRANSCRIPT_PATH" "$BACKUP_FILE"
fi

# --- 2) Handoff fallback (compact 시 컨텍스트 보존) ---
HANDOFF_DIR="${PROJECT_ROOT}/.claude/handoff"
LATEST="${HANDOFF_DIR}/latest.md"
GIT_BRANCH="$(git branch --show-current 2>/dev/null || echo "N/A")"
GIT_DIFF_STAT="$(git diff --stat 2>/dev/null || echo "N/A")"
GIT_LOG="$(git log --oneline -3 2>/dev/null || echo "N/A")"

# latest.md가 이미 있으면 (Claude가 /handoff로 작성) 덮어쓰지 않음
if [[ ! -f "$LATEST" ]]; then
    mkdir -p "$HANDOFF_DIR"

    cat > "$LATEST" << EOF
# Handoff: ${PROJECT_NAME} (auto-generated on compact)
- Date: $(date '+%Y-%m-%d %H:%M')
- Session: ${SHORT_ID}
- Branch: ${GIT_BRANCH}
- cwd: ${PROJECT_ROOT}

## 진행 중이던 작업
(compact 전 자동 생성 — 상세 컨텍스트는 transcript 백업 참조)

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

# --- 3) Obsidian 세션 스냅샷 ---
# compact 직전에 transcript를 압축 저장해, 긴 대화에서도 다음 세션이 최신 맥락을 읽을 수 있게 한다.
OBSIDIAN_VAULT="${OBSIDIAN_VAULT:-${HOME}/Documents/Obsidian Vault}"
OBSIDIAN_SESSION_SUBDIR="${OBSIDIAN_SESSION_SUBDIR:-00_session}"
AI_ENV_BIN=( )
if command -v ai-env >/dev/null 2>&1; then
    AI_ENV_BIN=(ai-env)
elif command -v uv >/dev/null 2>&1; then
    AI_ENV_HOME="${AI_ENV_HOME:-${HOME}/work/glasslego/ai-env}"
    if [[ -d "$AI_ENV_HOME" ]]; then
        AI_ENV_BIN=(uv --directory "$AI_ENV_HOME" run ai-env)
    fi
fi

if [[ ${#AI_ENV_BIN[@]} -gt 0 ]]; then
    AI_ENV_SESSION_NOTE=$(
        cat << EOF
coding agent pre-compact snapshot

agent: ${AI_ENV_AGENT_NAME:-claude}
session_id: ${SESSION_ID}
transcript_path: ${TRANSCRIPT_PATH:-"(not provided)"}
cwd: ${PROJECT_ROOT}
branch: ${GIT_BRANCH}
handoff: ${LATEST}
EOF
    )
    "${AI_ENV_BIN[@]}" session save \
        --note "$AI_ENV_SESSION_NOTE" \
        --vault "$OBSIDIAN_VAULT" \
        --subdir "$OBSIDIAN_SESSION_SUBDIR" \
        --cwd "$PROJECT_ROOT" \
        --agent "${AI_ENV_AGENT_NAME:-claude}" \
        --session-id "$SESSION_ID" \
        --transcript-path "$TRANSCRIPT_PATH" \
        >/dev/null 2>&1 || true
fi
