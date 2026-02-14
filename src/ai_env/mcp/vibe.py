"""claude --fallback 쉘 함수 생성기"""

from __future__ import annotations


def generate_shell_functions(agent_priority: list[str]) -> str:
    """에이전트 우선순위 기반 claude --fallback 쉘 함수 생성

    settings.yaml의 agent_priority 순서대로 AI 에이전트를 시도하는
    'claude()' 쉘 함수를 생성합니다. --fallback 플래그 없이 호출하면
    원본 claude 바이너리로 passthrough합니다.
    --fallback 모드에서는 앞 순위 에이전트가 비정상 종료(세션 한도 등)하면
    다음 에이전트로 자동 전환되며, Claude rate-limit 해제 후 자동 복귀를 시도합니다.

    Args:
        agent_priority: 에이전트 우선순위 리스트 (예: ["claude", "codex"])

    Returns:
        bash 함수 문자열
    """
    if not agent_priority:
        return ""

    agents_str = " ".join(f'"{a}"' for a in agent_priority)
    priority_display = " → ".join(agent_priority)

    return f"""\
# === AI Agent Fallback (claude --fallback) ===
# Priority: {priority_display}
# Usage: claude --fallback [args...]           - 우선순위대로 에이전트 시도, 실패 시 자동 전환
#        claude --fallback --to gemini [args..] - fallback 대상 지정 (쉼표 구분 가능: gemini,codex)
#        claude --fallback -2 [args...]         - 2순위 에이전트부터 시작 (예: codex)
#        claude --fallback -l                   - 에이전트 우선순위 목록 출력
#        claude [args...]                       - 일반 claude 실행 (passthrough)
# Env:   CLAUDE_FALLBACK_RETRY_MINUTES (default: 15)
claude() {{
    # --fallback 없으면 원본 claude 바이너리로 passthrough
    if [[ "$1" != "--fallback" ]]; then
        command claude "$@"
        return $?
    fi
    shift  # --fallback 소비

    local agents=({agents_str})
    local start_idx=0
    local claude_retry_epoch=0
    local claude_retry_minutes="${{CLAUDE_FALLBACK_RETRY_MINUTES:-15}}"

    _claude_is_rate_limited() {{
        local log_file="$1"
        grep -Eiq \\
            "rate limit|usage limit|quota|too many requests|try again in|credit balance|token limit|exceeded" \\
            "$log_file"
    }}

    _run_agent() {{
        local agent="$1"; shift
        if [[ "$agent" == "claude" ]]; then
            command claude "$@"
        else
            "$agent" "$@"
        fi
    }}

    # 옵션 파싱
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -l|--list)
                printf '\\033[36mAgent priority:\\033[0m\\n'
                for i in "${{!agents[@]}}"; do
                    printf '  %d. %s\\n' "$((i+1))" "${{agents[$i]}}"
                done
                return 0
                ;;
            --to)
                shift
                if [[ -z "$1" ]]; then
                    printf '\\033[31m❌ --to 옵션에 에이전트를 지정하세요 (예: --to gemini)\\033[0m\\n'
                    return 1
                fi
                local IFS=','
                local fallback_targets=($1)
                unset IFS
                agents=("claude" "${{fallback_targets[@]}}")
                shift
                ;;
            -[0-9])
                start_idx=$((${{1#-}} - 1))
                shift
                ;;
            *)
                break
                ;;
        esac
    done
    local agent_args=("$@")

    while true; do
        local tried=0
        local switched_back_to_claude=0

        for ((i=start_idx; i<${{#agents[@]}}; i++)); do
            local agent="${{agents[$i]}}"
            local now_epoch
            now_epoch=$(date +%s)

            # Claude가 rate limit 상태면 cooldown 기간 동안 건너뜀
            if [[ "$agent" == "claude" && $claude_retry_epoch -gt $now_epoch ]]; then
                continue
            fi

            # Claude Code는 중첩 세션 불가
            if [[ "$agent" == "claude" && -n "${{CLAUDECODE:-}}" ]]; then
                printf '\\033[33m⏭ %s: 이미 Claude Code 세션 내부 (건너뜀)\\033[0m\\n' "$agent"
                continue
            fi

            if ! command -v "$agent" &>/dev/null; then
                printf '\\033[33m⏭ %s: 설치되지 않음 (건너뜀)\\033[0m\\n' "$agent"
                continue
            fi

            tried=$((tried + 1))
            printf '\\033[36m🚀 Starting %s...\\033[0m\\n' "$agent"

            local log_file
            log_file=$(mktemp -t "claude-fb-${{agent}}.XXXXXX")

            _run_agent "$agent" "${{agent_args[@]}}" > >(tee "$log_file") 2>&1
            local exit_code=$?

            if [[ "$agent" == "claude" ]]; then
                if [[ $exit_code -ne 0 ]] && _claude_is_rate_limited "$log_file"; then
                    claude_retry_epoch=$((now_epoch + claude_retry_minutes * 60))
                    printf '\\n\\033[33m⚠ claude rate-limit 감지. %s분 후 재시도 예정\\033[0m\\n\\n' "$claude_retry_minutes"
                else
                    claude_retry_epoch=0
                fi
            fi
            rm -f "$log_file"

            if [[ $exit_code -eq 0 ]]; then
                # fallback 에이전트(codex 등) 세션 종료 후 Claude cooldown이 풀렸다면 자동 복귀
                now_epoch=$(date +%s)
                if [[ "$agent" != "claude" && $claude_retry_epoch -gt 0 && $now_epoch -ge $claude_retry_epoch ]]; then
                    printf '\\n\\033[36m🔁 Claude 제한 해제 감지. claude로 복귀합니다...\\033[0m\\n\\n'
                    start_idx=0
                    switched_back_to_claude=1
                    break
                fi
                return 0
            fi

            printf '\\n\\033[33m⚠ %s 종료 (code: %d). 다음 에이전트로 전환...\\033[0m\\n\\n' "$agent" "$exit_code"
        done

        if [[ $switched_back_to_claude -eq 1 ]]; then
            continue
        fi

        if [[ $tried -eq 0 ]]; then
            if [[ $claude_retry_epoch -gt 0 ]]; then
                now_epoch=$(date +%s)
                local wait_sec=$((claude_retry_epoch - now_epoch))
                if [[ $wait_sec -gt 0 ]]; then
                    printf '\\033[33m⏳ Claude 제한 해제 대기 중... %d초 후 재시도\\033[0m\\n' "$wait_sec"
                    sleep "$wait_sec"
                    start_idx=0
                    continue
                fi
            fi
            printf '\\033[31m❌ 사용 가능한 AI 에이전트가 없습니다\\033[0m\\n'
            return 1
        fi

        # 한 라운드가 끝났고 Claude cooldown이 풀렸다면 Claude부터 재시도
        now_epoch=$(date +%s)
        if [[ $claude_retry_epoch -gt 0 && $now_epoch -ge $claude_retry_epoch ]]; then
            start_idx=0
            continue
        fi

        printf '\\033[31m❌ 모든 AI 에이전트 소진\\033[0m\\n'
        return 1
    done
}}"""
