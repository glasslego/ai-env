#!/usr/bin/env bash
# 양 도구 공용 응답 기록. JSON stdin을 CLI에 전달하고 제어/추론 로그는 읽지 않는다.
set -euo pipefail
AI_ENV_DIR="${AI_ENV_DIR:-${HOME}/work/glasslego/ai-env}"
AGENT="${1:?agent must be codex or claude}"
if [[ ! -x "${AI_ENV_DIR}/.venv/bin/ai-env" ]]; then
    printf '%s\n' '{"systemMessage":"공용 세션 기록 실패: ai-env 가상환경 실행 파일이 없습니다."}'
    exit 0
fi
exec "${AI_ENV_DIR}/.venv/bin/ai-env" session hook --agent "$AGENT"
