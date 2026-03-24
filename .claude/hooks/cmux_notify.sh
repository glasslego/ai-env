#!/usr/bin/env bash
# cmux_notify.sh — Claude Code → cmux 알림 브릿지
# Agent Teams + Subagent 이벤트를 cmux notify/log/status로 전달
#
# 지원 이벤트:
#   SessionStart     — 사이드바 상태 "running"
#   Stop             — OS 알림 + 상태 "idle"
#   SubagentStart    — teammate/subagent 생성 로그
#   SubagentStop     — teammate/subagent 완료 알림
#   TeammateIdle     — teammate idle 감지 로그
#   TaskCompleted    — task 완료 로그
#   PostToolUse      — Task/Agent tool 완료 로그
#   Notification     — Claude 내부 알림 전달
#
# 사용 환경: cmux 터미널 안에서 Claude Code 실행 시 자동 동작
# cmux 밖에서는 조용히 종료 (exit 0)

set -euo pipefail

# cmux 환경이 아니면 skip
command -v cmux &>/dev/null || exit 0
[[ -n "${CMUX_WORKSPACE_ID:-}" ]] || exit 0

INPUT="$(cat)"
HOOK_EVENT="$(echo "$INPUT" | jq -r '.hook_event_name // "unknown"')"
TOOL_NAME="$(echo "$INPUT" | jq -r '.tool_name // ""')"
STOP_REASON="$(echo "$INPUT" | jq -r '.stop_reason // ""')"
SESSION_ID="$(echo "$INPUT" | jq -r '.session_id // ""')"
SHORT_ID="${SESSION_ID:0:8}"

# 프로젝트 이름 추출
PROJECT_NAME="$(basename "$(git rev-parse --show-toplevel 2>/dev/null || echo "$PWD")")"

# teammate/agent 이름 추출 헬퍼
AGENT_ID="$(echo "$INPUT" | jq -r '.agent_id // ""')"
AGENT_TYPE="$(echo "$INPUT" | jq -r '.agent_type // ""')"
TEAMMATE_NAME="$(echo "$INPUT" | jq -r '.teammate_name // .agent_description // ""')"
AGENT_LABEL="${TEAMMATE_NAME:-${AGENT_TYPE:-${AGENT_ID:0:8}}}"

case "$HOOK_EVENT" in
    Stop)
        # 세션 종료 알림
        cmux notify \
            --title "Claude Code [$PROJECT_NAME]" \
            --body "세션 완료 ($SHORT_ID): ${STOP_REASON:-normal}"

        cmux set-status "claude" "idle" --icon "checkmark.circle" --color "#4CAF50" 2>/dev/null || true
        cmux clear-progress 2>/dev/null || true
        cmux log --level info --source "claude" "세션 종료: ${STOP_REASON:-normal} ($SHORT_ID)" 2>/dev/null || true
        ;;

    SubagentStart)
        # Teammate/subagent 생성 — 사이드바 상태 업데이트 + 로그
        cmux set-status "claude-team" "teammate: $AGENT_LABEL" --icon "person.2.fill" --color "#FF9800" 2>/dev/null || true
        cmux log --level info --source "claude-team" "teammate 시작: $AGENT_LABEL" 2>/dev/null || true
        ;;

    SubagentStop)
        # Teammate/subagent 완료 알림
        cmux notify \
            --title "Teammate 완료 [$PROJECT_NAME]" \
            --body "$AGENT_LABEL: ${STOP_REASON:-done}"

        cmux log --level info --source "claude-team" "teammate 완료: $AGENT_LABEL (${STOP_REASON:-done})" 2>/dev/null || true
        cmux clear-status "claude-team" 2>/dev/null || true
        ;;

    TeammateIdle)
        # Teammate가 할 일이 없어서 idle 상태
        cmux log --level warn --source "claude-team" "teammate idle: $AGENT_LABEL" 2>/dev/null || true
        cmux set-status "claude-team" "idle: $AGENT_LABEL" --icon "pause.circle" --color "#9E9E9E" 2>/dev/null || true
        ;;

    TaskCompleted)
        # Task 완료 이벤트 (Agent Teams의 task 시스템)
        TASK_NAME="$(echo "$INPUT" | jq -r '.task_name // .task_description // "task"')"
        COMPLETED_BY="$(echo "$INPUT" | jq -r '.completed_by // "unknown"')"
        cmux notify \
            --title "Task 완료 [$PROJECT_NAME]" \
            --body "$TASK_NAME (by $COMPLETED_BY)"

        cmux log --level info --source "claude-task" "완료: $TASK_NAME (by $COMPLETED_BY)" 2>/dev/null || true
        ;;

    PostToolUse)
        # Task/Agent tool 완료 시 로그
        if [[ "$TOOL_NAME" == "Task" || "$TOOL_NAME" == "Agent" ]]; then
            TASK_DESC="$(echo "$INPUT" | jq -r '.tool_input.description // "task"')"
            cmux log --level info --source "claude-task" "완료: $TASK_DESC" 2>/dev/null || true
        fi
        ;;

    Notification)
        # Claude Code 내부 알림 전달
        MSG="$(echo "$INPUT" | jq -r '.message // .notification // "알림"')"
        cmux notify \
            --title "Claude [$PROJECT_NAME]" \
            --body "$MSG"
        ;;

    SessionStart)
        # 세션 시작 상태 표시
        cmux set-status "claude" "running" --icon "bolt.fill" --color "#2196F3" 2>/dev/null || true
        cmux log --level info --source "claude" "세션 시작 ($SHORT_ID)" 2>/dev/null || true
        ;;
esac

exit 0
