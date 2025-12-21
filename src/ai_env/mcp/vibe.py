"""claude --fallback 쉘 함수 생성기"""

from __future__ import annotations


def _format_entry(entry: str) -> str:
    """agent:model 엔트리를 표시용 문자열로 변환

    Args:
        entry: 에이전트 엔트리 (예: "claude", "claude:sonnet", "codex")

    Returns:
        표시용 문자열 (예: "claude", "claude (sonnet)", "codex")
    """
    if ":" in entry:
        base, model = entry.split(":", 1)
        return f"{base} ({model})"
    return entry


def generate_shell_functions(
    agent_priority: list[str],
    fallback_log_dir: str | None = None,
) -> str:
    """에이전트 우선순위 기반 claude --fallback 쉘 함수 생성

    settings.yaml의 agent_priority 순서대로 AI 에이전트를 시도하는
    'claude()' 쉘 함수를 생성합니다. --fallback 플래그 없이 호출하면
    원본 claude 바이너리로 passthrough합니다.
    --fallback 모드에서는 앞 순위 에이전트가 비정상 종료(세션 한도 등)하면
    다음 에이전트로 자동 전환되며, Claude rate-limit 해제 후 자동 복귀를 시도합니다.

    "agent:model" 형식으로 동일 에이전트의 다른 모델을 지정할 수 있습니다.
    예: "claude:sonnet" → claude --model sonnet으로 실행

    Args:
        agent_priority: 에이전트 우선순위 리스트
            (예: ["claude", "claude:sonnet", "codex"])
        fallback_log_dir: 세션 로그/핸드오프 저장 디렉토리 (None이면 temp 사용)

    Returns:
        bash 함수 문자열
    """
    if not agent_priority:
        return ""

    agents_str = " ".join(f'"{a}"' for a in agent_priority)
    priority_display = " → ".join(_format_entry(a) for a in agent_priority)
    log_dir_default = fallback_log_dir or ""

    return f"""\
# === AI Agent Skills Sync ===
# 인터랙티브 TTY에서는 sync를 먼저 보여주고, 비대화형에서는 조용히 백그라운드 실행
# claude(), codex() wrapper에서 자동 호출
_ai_env_sync_skills_run() {{
    local _ai_env_dir="$1"
    local _lock="$2"

    touch "$_lock"
    cd "$_ai_env_dir"
    # nullglob: 매칭 없으면 빈 배열 (zsh no-match 에러 방지)
    setopt nullglob 2>/dev/null || shopt -s nullglob 2>/dev/null || true
    for d in cde-*skills; do
        [[ -d "$d/.git" ]] && git -C "$d" pull --ff-only --quiet 2>/dev/null || true
    done
    uv run ai-env sync --skills-only --skills-all 2>/dev/null
}}

_ai_env_sync_skills() {{
    local _mode="${{1:-auto}}"
    local _ai_env_dir="${{HOME}}/work/glasslego/ai-env"
    local _lock="/tmp/.ai_env_skills_sync.lock"
    local _run_foreground=0

    case "$_mode" in
        foreground)
            _run_foreground=1
            ;;
        background)
            _run_foreground=0
            ;;
        auto)
            if [[ -t 0 && -t 1 ]]; then
                _run_foreground=1
            fi
            ;;
    esac

    # 5분 이내 동기화 했으면 스킵 (중복 방지)
    if [[ -f "$_lock" ]]; then
        local _age=$(( $(date +%s) - $(stat -f%m "$_lock" 2>/dev/null || echo 0) ))
        [[ $_age -lt 300 ]] && return 0
    fi
    [[ ! -d "$_ai_env_dir" ]] && return 0

    if [[ $_run_foreground -eq 1 ]]; then
        _ai_env_sync_skills_run "$_ai_env_dir" "$_lock"
    else
        (
            _ai_env_sync_skills_run "$_ai_env_dir" "$_lock"
        ) >/dev/null 2>&1 &
    fi
}}

# === AI Agent Fallback (claude --fallback) ===
# Priority: {priority_display}
# Usage: claude --fallback [args...]           - 우선순위대로 에이전트 시도, 실패 시 자동 전환
#        claude --fallback --to gemini [args..] - fallback 대상 지정 (쉼표 구분 가능: gemini,codex)
#        claude --fallback -2 [args...]         - 2순위 에이전트부터 시작 (예: codex)
#        claude --fallback --auto [args...]      - 모든 에이전트 자동 승인 모드 (권한 확인 건너뜀)
#        claude --fallback -l                   - 에이전트 우선순위 목록 출력
#        claude [args...]                       - 일반 claude 실행 (passthrough)
# Model: "agent:model" 형식으로 모델 지정 가능 (예: claude:sonnet → claude --model sonnet)
# Env:   CLAUDE_FALLBACK_RETRY_MINUTES (default: 15)
#        CLAUDE_FALLBACK_AUTO (default: 0) - 1이면 --auto 모드 기본 활성화
#        CLAUDE_FALLBACK_LOG_DIR - 세션 로그/핸드오프 저장 경로
claude() {{
    # 팀 스킬 동기화 (백그라운드)
    _ai_env_sync_skills
    # --fallback 없으면 원본 claude 바이너리로 passthrough
    if [[ "$1" != "--fallback" ]]; then
        command claude "$@"
        return $?
    fi
    shift  # --fallback 소비

    # zsh 호환: 0-based 배열 인덱싱 (bash와 동일하게)
    [[ -n "${{ZSH_VERSION:-}}" ]] && setopt localoptions KSH_ARRAYS 2>/dev/null

    # fallback 실행 중 xtrace(set -x) 출력이 TUI를 깨뜨리지 않도록 일시 비활성화
    local _saved_xtrace=0
    if [[ $- == *x* ]]; then
        _saved_xtrace=1
        set +x
    fi

    local agents=({agents_str})
    local start_idx=0
    local claude_retry_minutes="${{CLAUDE_FALLBACK_RETRY_MINUTES:-15}}"
    local auto_mode="${{CLAUDE_FALLBACK_AUTO:-0}}"

    # 터미널 상태 보존 + 시그널 트랩 (kill/Ctrl+C 시에도 터미널 복원)
    local _saved_stty
    _saved_stty=$(stty -g 2>/dev/null || true)
    trap 'stty "$_saved_stty" 2>/dev/null; printf "\\033[0m\\033[?25h\\r" 2>/dev/null; [[ "${{_saved_xtrace:-0}}" -eq 1 ]] && set -x 2>/dev/null' INT TERM HUP

    # 세션 로그/핸드오프 저장 경로 (미설정 시 기존 temp 동작)
    local _fb_log_dir="${{CLAUDE_FALLBACK_LOG_DIR:-{log_dir_default}}}"
    _fb_log_dir="${{_fb_log_dir/#\\~/$HOME}}"
    local _fallback_session_id=""

    # Per-entry cooldown epochs (각 엔트리별 독립 cooldown)
    local -a entry_cooldown_epochs=()
    for ((j=0; j<${{#agents[@]}}; j++)); do
        entry_cooldown_epochs[$j]=0
    done

    _parse_agent_entry() {{
        # "claude:sonnet" → base_agent=claude, model_suffix=sonnet
        # "claude"        → base_agent=claude, model_suffix=""
        # "codex"         → base_agent=codex,  model_suffix=""
        local entry="$1"
        base_agent="${{entry%%:*}}"
        model_suffix="${{entry#*:}}"
        [[ "$model_suffix" == "$entry" ]] && model_suffix=""
    }}

    _strip_ansi() {{
        # ANSI/제어 시퀀스 제거: CSI, OSC, charset, CR, 제어문자
        sed -E $'s/\\x1b\\\\[[0-9;?]*[a-zA-Z]//g; s/\\x1b\\\\][^\\x07]*\\x07//g; s/\\x1b\\\\(B//g; s/\\\\r//g' 2>/dev/null
    }}

    _restore_xtrace() {{
        [[ $_saved_xtrace -eq 1 ]] && set -x
    }}

    _claude_is_rate_limited() {{
        local log_file="$1"
        local strict="${{2:-0}}"
        local mode="${{3:-post}}"  # post | realtime
        # Claude Code 한도 초과/요금량 제한 핵심 패턴
        local _strong_rate_patterns="/rate-limit-option(s)?|/reset-rate-limit|what.?do.?you.?want.?to.?do|switch.?to.?extra.?usage|upgrade.?your.?plan|stop.?and.?wait.?for.?limit.?to.?reset|hit.?your.?limit|you.?ve.?hit.?your.?limit|you.?have.?hit.?your.?limit|you.?have.?exhausted|you.?have.?exceeded"
        local _strict_rate_patterns="${{_strong_rate_patterns}}|too.?many.?requests|requests?.?per.?minute|quota.{{0,24}}(exceeded|reached|exhausted|limit)|request.{{0,24}}(limit|quota|reached|exceeded)|usage.{{0,24}}(limit|quota|reached|exceeded)|(exhausted|exceeded|reached).{{0,24}}(your.{{0,20}})?(quota|limit|request)|limit.{{0,24}}(reached|exceeded|hit)"
        local _rate_limit_patterns="${{_strict_rate_patterns}}|rate[- ]limit|usage[- ]limit|usage[- ]quota|request[- ]limit|request[- ]quota|(reached|exceeded|hit|exhausted|over).{{0,16}}(hourly|daily|weekly|monthly).?limit|(hourly|daily|weekly|monthly).?limit.{{0,16}}(reached|exceeded|hit|exhausted)|quota.{{0,24}}(used|exceeded|reached|exhausted)|reached.{{0,24}}your.{{0,24}}(usage|quota|request|limit)|exceeded.{{0,24}}your.{{0,24}}(usage|quota|request|limit)"
        # realtime 모니터는 TUI 리드로잉으로 끝부분이 오염될 수 있어 더 넓은 창을 검사
        local _tail_n=50
        local _patterns="${{_rate_limit_patterns}}"
        if [[ "$mode" == "realtime" ]]; then
            _tail_n=300
            _patterns="${{_strong_rate_patterns}}"
        elif [[ "$strict" -eq 1 ]]; then
            _patterns="${{_strict_rate_patterns}}"
        fi
        local _cleaned
        _cleaned=$(tail -n "$_tail_n" "$log_file" 2>/dev/null | _strip_ansi)
        echo "$_cleaned" | command grep -Eiq "${{_patterns}}"
    }}

    _resolve_bin() {{
        # 쉘 함수를 우회하여 실제 바이너리 경로 반환
        if [[ -n "${{ZSH_VERSION:-}}" ]]; then
            whence -p "$1" 2>/dev/null
        else
            type -P "$1" 2>/dev/null
        fi
    }}

    _kill_process_tree() {{
        # macOS 기본 도구(pgrep)로 프로세스 트리를 재귀 종료
        local root_pid="$1"
        local sig="${{2:-TERM}}"
        local child_pid

        for child_pid in $(pgrep -P "$root_pid" 2>/dev/null || true); do
            _kill_process_tree "$child_pid" "$sig"
        done

        kill -"$sig" "$root_pid" 2>/dev/null || true
    }}

    _get_claude_session_id() {{
        # Claude Code 세션 ID 추출 (최근 .jsonl 파일명의 앞 8자)
        local project_dir="$HOME/.claude/projects/$(pwd | sed 's|/|-|g')"
        if [[ -d "$project_dir" ]]; then
            local latest
            latest=$(ls -t "$project_dir"/*.jsonl 2>/dev/null | head -1)
            if [[ -n "$latest" ]]; then
                basename "$latest" .jsonl | cut -c1-8
                return
            fi
        fi
        # fallback: PID+timestamp 해시
        echo "$$$(date +%s)" | shasum | cut -c1-8
    }}

    _create_handoff_file() {{
        # 에이전트 전환 시 세션 컨텍스트를 파일로 저장
        # 다음 에이전트가 이 파일을 읽고 이어서 작업할 수 있도록 함
        local from_agent="$1"
        local log_file="$2"
        shift 2
        local original_args=("$@")

        local hf
        if [[ -n "$_fb_log_dir" ]]; then
            mkdir -p "$_fb_log_dir"
            [[ -z "$_fallback_session_id" ]] && _fallback_session_id=$(_get_claude_session_id)
            hf="${{_fb_log_dir}}/${{_fallback_session_id}}_handoff.md"
        else
            hf=$(mktemp -t "claude-fb-handoff.XXXXXX.md")
        fi

        {{
            local _from_base="${{from_agent%%:*}}"
            if [[ "$_from_base" == "claude" ]]; then
                echo "# Handoff: Claude Code → Fallback Agent"
                echo ""
                echo "Claude Code가 rate-limit으로 중단되었습니다. 아래 컨텍스트를 참고하여 이어서 작업하세요."
            else
                echo "# Handoff: $from_agent → Claude Code"
                echo ""
                echo "$from_agent 세션이 종료되고 Claude 제한이 해제되어 복귀합니다. 아래 컨텍스트를 참고하여 이어서 작업하세요."
            fi
            echo ""
            echo "## Original Task"
            if [[ ${{#original_args[@]}} -gt 0 ]]; then
                printf '%s ' "${{original_args[@]}}"
                echo ""
            else
                echo "(대화형 세션 — 아래 세션 출력 참고)"
            fi
            echo ""

            # Git context
            if git rev-parse --is-inside-work-tree &>/dev/null 2>&1; then
                local ds
                ds=$(git diff --stat 2>/dev/null)
                local cs
                cs=$(git diff --cached --stat 2>/dev/null)
                if [[ -n "$ds" || -n "$cs" ]]; then
                    echo "## Changes Made So Far"
                    echo '```'
                    [[ -n "$cs" ]] && echo "Staged:" && echo "$cs"
                    [[ -n "$ds" ]] && echo "Unstaged:" && echo "$ds"
                    echo '```'
                    echo ""
                fi
                local fd
                fd=$(git diff HEAD 2>/dev/null | head -300)
                if [[ -n "$fd" ]]; then
                    echo "## Diff Detail"
                    echo '```diff'
                    echo "$fd"
                    echo '```'
                    echo ""
                fi
            fi

            # 세션 로그 (ANSI/TUI 정리, 의미 있는 마지막 30줄)
            # script -qF PTY 캡처는 TUI 리드로잉이 포함되어 공격적 정리 필요:
            # 1) ANSI 이스케이프 + CR 제거, 제어 문자 제거
            # 2) 빈 줄/짧은 줄 제거 (TUI 스피너·커서 잔해)
            # 3) TUI 노이즈 제거: 상태 표시, 도구 호출, 수평선, 토큰 카운터 등
            # NOTE: command grep 필수 — 사용자 alias(grep -n)가 라인번호를 주입함
            if [[ -f "$log_file" ]]; then
                local cl
                cl=$(_strip_ansi < "$log_file" \\
                     | tr -d $'\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f' \\
                     | command grep -v '^[[:space:]]*$' \\
                     | awk 'length >= 40' \\
                     | command grep -vEi 'Embellishing|Gesticulating|Meditating|Ruminating|Pondering|Deliberating' \\
                     | command grep -vE 'bypass permissions|shift\\+tab|ctrl\\+o to expand|esc to interrupt' \\
                     | command grep -vE '[─━═]{{20,}}' \\
                     | command grep -vE '(Read|Search|Rd|Glob|Grep|Write|Edit|Bash|Update)\\(' \\
                     | command grep -vE 'Waiting…|tokens.*thought|thought for [0-9]|[↓↑].*tokens|Context left until' \\
                     | command grep -vE 'Pasting text|[▐▛█▜▌▘▝❯⏺⎿✻✶✽✳✢]|^warn: CPU lacks' \\
                     | sed -E 's/[[:space:]]+$//' \\
                     | tail -n 30)
                if [[ -n "$cl" ]]; then
                    echo "## Last Session Output"
                    echo '```'
                    echo "$cl"
                    echo '```'
                    echo ""
                fi
            fi

            echo "## Instructions"
            echo "1. 위 컨텍스트를 읽고 현재 상태를 파악하세요"
            echo "2. 코드베이스의 현재 상태를 확인하세요"
            echo "3. 중단된 작업을 이어서 진행하세요"
        }} > "$hf"

        echo "$hf"
    }}

    _user_explicitly_exited() {{
        # 세션 로그에서 사용자의 명시적 종료 명령 (/exit, /quit) 검색
        local log_file="$1"
        [[ ! -f "$log_file" ]] && return 1
        tail -n 20 "$log_file" 2>/dev/null \\
            | _strip_ansi \\
            | command grep -qiE '/exit|/quit'
    }}

    _parse_model_from_log() {{
        # 세션 로그에서 Claude 시작 배너의 모델명 추출
        # 예: "Opus 4.6 · Claude Max" → "opus", "Sonnet 4.6 · Claude Max" → "sonnet"
        local log_file="$1"
        local _model
        _model=$(head -n 30 "$log_file" 2>/dev/null \
            | _strip_ansi \
            | command grep -oEi '(Opus|Sonnet|Haiku)[[:space:]]+[0-9]+' \
            | head -1 \
            | awk '{{print tolower($1)}}')
        echo "${{_model:-}}"
    }}

    _save_session_log() {{
        # 세션 로그를 영구 저장 디렉토리에 복사
        # agent_name에 모델명이 없는 경우 (plain "claude") 로그에서 파싱해 추가
        local log_file="$1"
        local agent_name="$2"
        [[ -z "$_fb_log_dir" || ! -f "$log_file" ]] && return 0
        mkdir -p "$_fb_log_dir"
        [[ -z "$_fallback_session_id" ]] && _fallback_session_id=$(_get_claude_session_id)
        # plain "claude" 엔트리: 로그에서 실제 모델명 추출해 파일명에 포함
        if [[ "$agent_name" == "claude" ]]; then
            local _model
            _model=$(_parse_model_from_log "$log_file")
            [[ -n "$_model" ]] && agent_name="claude-${{_model}}"
        fi
        local perm_log="${{_fb_log_dir}}/${{_fallback_session_id}}_${{agent_name}}.log"
        command cp -f "$log_file" "$perm_log" < /dev/null 2>/dev/null
        printf '\\r\\033[36m📝 세션 로그: %s\\033[0m\\r\\n' "$perm_log"
    }}

    _parse_reset_epoch() {{
        # 세션 로그에서 "resets [날짜/시간]" 파싱 → 리셋 시각 epoch 반환
        # macOS date -j 사용 (BSD date). 파싱 실패 시 return 1
        local log_file="$1"
        [[ ! -f "$log_file" ]] && return 1
        local _cleaned
        _cleaned=$(tail -n 50 "$log_file" 2>/dev/null | _strip_ansi)
        # "resets Feb 23 at 9am" 형태 (날짜+시간)
        local _match
        _match=$(echo "$_cleaned" | command grep -oEi 'resets? +(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) +[0-9]+ +at +[0-9]+[ap]m' | head -1)
        if [[ -n "$_match" ]]; then
            local _month _day _time _hour _ampm _year _reset_ep
            _month=$(echo "$_match" | awk '{{print $2}}')
            _day=$(echo "$_match" | awk '{{print $3}}')
            _time=$(echo "$_match" | command grep -oEi '[0-9]+[ap]m$')
            _hour=$(echo "$_time" | command grep -oE '^[0-9]+')
            _ampm=$(echo "$_time" | command grep -oEi '[ap]m$' | tr '[:lower:]' '[:upper:]')
            [[ ${{#_hour}} -eq 1 ]] && _hour="0$_hour"
            _year=$(date +%Y)
            _reset_ep=$(date -j -f "%b %d %I%p %Y" "$_month $_day ${{_hour}}${{_ampm}} $_year" +%s 2>/dev/null)
            if [[ -n "$_reset_ep" ]]; then
                local _now=$(date +%s)
                # 이미 1일 이상 지난 시각이면 내년으로 보정
                if [[ $((_now - _reset_ep)) -gt 86400 ]]; then
                    _reset_ep=$(date -j -f "%b %d %I%p %Y" "$_month $_day ${{_hour}}${{_ampm}} $((_year + 1))" +%s 2>/dev/null)
                fi
                [[ -n "$_reset_ep" ]] && echo "$_reset_ep" && return 0
            fi
        fi

        # "resets 2pm" 형태 (시간만 → 오늘 또는 내일)
        _match=$(echo "$_cleaned" | command grep -oEi 'resets? +[0-9]+[ap]m' | head -1)
        if [[ -n "$_match" ]]; then
            local _time _hour _ampm _reset_ep
            _time=$(echo "$_match" | command grep -oEi '[0-9]+[ap]m$')
            _hour=$(echo "$_time" | command grep -oE '^[0-9]+')
            _ampm=$(echo "$_time" | command grep -oEi '[ap]m$' | tr '[:lower:]' '[:upper:]')
            [[ ${{#_hour}} -eq 1 ]] && _hour="0$_hour"
            _reset_ep=$(date -j -f "%b %d %I%p %Y" "$(date '+%b %d') ${{_hour}}${{_ampm}} $(date +%Y)" +%s 2>/dev/null)
            if [[ -n "$_reset_ep" ]]; then
                local _now=$(date +%s)
                [[ $_reset_ep -lt $_now ]] && _reset_ep=$((_reset_ep + 86400))
                echo "$_reset_ep"
                return 0
            fi
        fi

        return 1
    }}

    _release_handoff() {{
        # 이전 핸드오프 파일 정리 (log_dir 있으면 보관, 없으면 삭제)
        if [[ -n "$_fb_log_dir" ]]; then
            handoff_file=""
        else
            [[ -n "$handoff_file" ]] && rm -f "$handoff_file" && handoff_file=""
        fi
    }}

    _save_cooldown_state() {{
        # cooldown 상태를 파일로 영속 저장 (다음 세션에서 복원)
        [[ -z "$_fb_log_dir" ]] && return 0
        mkdir -p "$_fb_log_dir" 2>/dev/null
        local _cf="${{_fb_log_dir}}/.fallback_cooldown"
        : > "$_cf"
        for ((j=0; j<${{#agents[@]}}; j++)); do
            [[ ${{entry_cooldown_epochs[$j]}} -gt 0 ]] && printf '%s\\t%s\\n' "${{agents[$j]}}" "${{entry_cooldown_epochs[$j]}}" >> "$_cf"
        done
    }}

    _load_cooldown_state() {{
        # 이전 세션의 cooldown 상태 복원
        [[ -z "$_fb_log_dir" ]] && return 0
        local _cf="${{_fb_log_dir}}/.fallback_cooldown"
        [[ ! -f "$_cf" ]] && return 0
        local now_epoch=$(date +%s)
        local _loaded=0
        while IFS=$'\\t' read -r _agent _epoch; do
            [[ -z "$_agent" || -z "$_epoch" ]] && continue
            for ((j=0; j<${{#agents[@]}}; j++)); do
                if [[ "${{agents[$j]}}" == "$_agent" && $_epoch -gt $now_epoch ]]; then
                    entry_cooldown_epochs[$j]=$_epoch
                    _loaded=1
                fi
            done
        done < "$_cf"
        # 만료된 cooldown 항목 정리 (파일에 유효한 것만 남김)
        _save_cooldown_state
        if [[ $_loaded -eq 1 ]]; then
            printf '\\r\\033[36mℹ 이전 세션 cooldown 상태 복원됨\\033[0m\\r\\n'
        fi
    }}

    # 옵션 파싱
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -l|--list)
                printf '\\033[36mAgent priority:\\033[0m\\n'
                for ((i=0; i<${{#agents[@]}}; i++)); do
                    _parse_agent_entry "${{agents[$i]}}"
                    if [[ -n "$model_suffix" ]]; then
                        printf '  %d. %s (%s)\\n' "$((i+1))" "$base_agent" "$model_suffix"
                    else
                        printf '  %d. %s\\n' "$((i+1))" "$base_agent"
                    fi
                done
                _restore_xtrace
                return 0
                ;;
            --to)
                shift
                if [[ -z "$1" ]]; then
                    printf '\\033[31m❌ --to 옵션에 에이전트를 지정하세요 (예: --to gemini)\\033[0m\\n'
                    _restore_xtrace
                    return 1
                fi
                local IFS=','
                local fallback_targets=($1)
                unset IFS
                agents=("claude" "${{fallback_targets[@]}}")
                # cooldown 배열 재초기화
                entry_cooldown_epochs=()
                for ((j=0; j<${{#agents[@]}}; j++)); do
                    entry_cooldown_epochs[$j]=0
                done
                shift
                ;;
            --auto)
                auto_mode=1
                shift
                ;;
            --dangerously-skip-permissions|--allow-dangerously-skip-permissions)
                # fallback wrapper 제어 플래그로 소비:
                # Claude에는 --dangerously-skip-permissions,
                # Codex에는 --yolo로 매핑한다.
                auto_mode=1
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
    local handoff_file=""
    local _reverse_handoff=0  # 1이면 non-Claude → Claude 방향 핸드오프

    # 매 세션 항상 Claude부터 시도 (이전 cooldown 무시)
    # 세션 내 cooldown은 entry_cooldown_epochs 메모리로 관리

    while true; do
        local tried=0
        local switched_back_to_claude=0

        for ((i=start_idx; i<${{#agents[@]}}; i++)); do
            local agent="${{agents[$i]}}"
            _parse_agent_entry "$agent"
            local now_epoch=$(date +%s)

            # 이 엔트리가 cooldown 상태면 건너뜀 (남은 시간 표시)
            if [[ "$base_agent" == "claude" && ${{entry_cooldown_epochs[$i]}} -gt $now_epoch ]]; then
                local _remain_min=$(( (entry_cooldown_epochs[$i] - now_epoch + 59) / 60 ))
                if [[ -n "$model_suffix" ]]; then
                    printf '\\r\\033[33m⏭ %s (%s): 한도 미복구 (약 %d분 후 재시도)\\033[0m\\r\\n' "$base_agent" "$model_suffix" "$_remain_min"
                else
                    printf '\\r\\033[33m⏭ %s: 한도 미복구 (약 %d분 후 재시도)\\033[0m\\r\\n' "$base_agent" "$_remain_min"
                fi
                continue
            fi

            # Claude Code는 중첩 세션 불가
            if [[ "$base_agent" == "claude" && -n "${{CLAUDECODE:-}}" ]]; then
                printf '\\r\\033[33m⏭ %s: 이미 Claude Code 세션 내부 (건너뜀)\\033[0m\\r\\n' "$agent"
                continue
            fi

            local agent_bin
            agent_bin=$(_resolve_bin "$base_agent")
            if [[ -z "$agent_bin" ]]; then
                printf '\\r\\033[33m⏭ %s: 설치되지 않음 (건너뜀)\\033[0m\\r\\n' "$agent"
                continue
            fi

            tried=$((tried + 1))
            if [[ -n "$model_suffix" ]]; then
                printf '\\r\\033[36m🚀 Starting %s (%s)...\\033[0m\\r\\n' "$base_agent" "$model_suffix"
            else
                printf '\\r\\033[36m🚀 Starting %s...\\033[0m\\r\\n' "$base_agent"
            fi

            # 핸드오프 컨텍스트가 있으면 다음 에이전트에 전달 (양방향)
            # Claude → Fallback: 항상 주입
            # Fallback → Claude: _reverse_handoff=1일 때만 주입 (Claude→Claude 전환 시 오주입 방지)
            local run_args=("${{agent_args[@]}}")
            if [[ -n "$handoff_file" && -f "$handoff_file" ]]; then
                local orig_prompt="${{agent_args[*]}}"
                if [[ "$base_agent" != "claude" ]]; then
                    run_args=("이전 Claude 세션이 rate-limit으로 중단됨. 원래 작업: ${{orig_prompt:-대화형 세션}}. 상세 컨텍스트(세션 로그, git diff)가 $handoff_file 에 저장됨. 이 파일을 먼저 읽고 이어서 작업하세요.")
                elif [[ -n "$model_suffix" && ${{#agent_args[@]}} -eq 0 ]]; then
                    # Claude model-level fallback(opus → sonnet)에서 대화형 입력 대기 방지:
                    # 원래 인자가 없으면 handoff 프롬프트를 자동 주입해 즉시 이어서 실행.
                    run_args=("이전 Claude 세션이 rate-limit으로 중단됨. 원래 작업: 대화형 세션. 상세 컨텍스트(세션 로그, git diff)가 $handoff_file 에 저장됨. 이 파일을 먼저 읽고 이어서 작업하세요.")
                elif [[ $_reverse_handoff -eq 1 ]]; then
                    run_args=("이전 에이전트에서 작업 수행됨. 원래 작업: ${{orig_prompt:-대화형 세션}}. 상세 컨텍스트(세션 로그, git diff)가 $handoff_file 에 저장됨. 이 파일을 먼저 읽고 이어서 작업하세요.")
                    _reverse_handoff=0
                fi
            fi
            # Codex:
            # - 프롬프트가 있으면 codex exec로 one-shot(non-interactive) 실행
            # - 프롬프트가 없으면 기존 TUI 모드(--yolo) 실행
            if [[ "$base_agent" == "codex" ]]; then
                if [[ ${{#run_args[@]}} -gt 0 ]]; then
                    local codex_prompt="${{run_args[*]}}"
                    run_args=(
                        "exec"
                        "-c"
                        "approval_policy='never'"
                        "-s"
                        "workspace-write"
                        "$codex_prompt"
                    )
                else
                    run_args=("--yolo" "--no-alt-screen")
                fi
            fi
            # --auto 모드: Claude 자동 승인 플래그 주입
            if [[ $auto_mode -eq 1 && "$base_agent" == "claude" ]]; then
                run_args=("--dangerously-skip-permissions" "${{run_args[@]}}")
            fi
            # Model suffix → --model 플래그 주입 (예: claude:sonnet → --model sonnet)
            if [[ -n "$model_suffix" && "$base_agent" == "claude" ]]; then
                run_args=("--model" "$model_suffix" "${{run_args[@]}}")
            fi

            local log_file=$(mktemp -t "claude-fb-${{base_agent}}.XXXXXX")
            local rate_limit_marker=$(mktemp -t "claude-fb-rl-${{base_agent}}.XXXXXX")
            rm -f "$rate_limit_marker"
            local monitor_pid=""

            # job monitor 비활성화: 백그라운드 모니터의 job notification 억제
            local exit_code=0
            local _saved_monitor=0
            [[ $- == *m* ]] && _saved_monitor=1
            set +m

            # Rate-limit 실시간 감지 모니터 (Claude 전용, 백그라운드)
            # pgrep으로 script 프로세스를 찾아 kill (log_file 경로가 유니크)
            if [[ "$base_agent" == "claude" ]]; then
                touch "$log_file"
                (
                    exec >/dev/null 2>&1
                    sleep 2
                    while true; do
                        script_pid=$(pgrep -f "script.*$log_file" 2>/dev/null | head -1)
                        [[ -z "$script_pid" ]] && break
                        if _claude_is_rate_limited "$log_file" 0 realtime; then
                            : > "$rate_limit_marker"
                            _kill_process_tree "$script_pid" INT
                            sleep 1
                            _kill_process_tree "$script_pid" TERM
                            sleep 1
                            _kill_process_tree "$script_pid" KILL
                            break
                        fi
                        sleep 1
                    done
                ) &
                monitor_pid=$!
            fi

            # script를 포그라운드 실행 → 터미널 stdin이 PTY로 정상 전달
            # (백그라운드 실행 시 script가 raw mode 전환 불가 → 입력 깨짐)
            # macOS script PTY 초기화 시 커서 column offset 방지
            printf '\\r' 2>/dev/null
            script -qF "$log_file" "$agent_bin" "${{run_args[@]}}"
            exit_code=$?

            # 터미널 상태 복원 (script PTY 종료 직후, 다른 출력보다 먼저)
            stty "$_saved_stty" 2>/dev/null || stty sane 2>/dev/null
            stty onlcr 2>/dev/null  # NL→CR-NL 변환 보장
            printf '\\033[0m\\033[?25h\\r\\n' 2>/dev/null

            if [[ -n "$monitor_pid" ]]; then
                kill "$monitor_pid" 2>/dev/null || true
                wait "$monitor_pid" 2>/dev/null || true
            fi
            [[ $_saved_monitor -eq 1 ]] && set -m

            # Claude: /exit, /quit 명시적 종료 → rate-limit 감지 건너뛰고 클린 종료
            # (rate-limit 메시지가 로그에 남아있어도 사용자 의도를 우선)
            if [[ "$base_agent" == "claude" ]] && _user_explicitly_exited "$log_file"; then
                entry_cooldown_epochs[$i]=0
                _save_cooldown_state
                _save_session_log "$log_file" "${{agent//:/-}}"
                rm -f "$log_file" "$rate_limit_marker"
                _release_handoff
                printf '\\033[36m👋 세션 종료\\033[0m\\n'
                _restore_xtrace
                return 0
            fi

            # Rate-limit 감지:
            # 1) 실시간 모니터 marker 있으면 무조건 rate-limit
            # 2) exit != 0: 일반 패턴으로 로그 검색
            # 3) exit == 0: strict 패턴만 (Claude UI 전용 문구만, 오탐 방지)
            if [[ "$base_agent" == "claude" ]]; then
                local _rl_now=$(date +%s)
                local _is_rl=0
                if [[ -f "$rate_limit_marker" ]]; then
                    _is_rl=1
                elif [[ $exit_code -ne 0 ]]; then
                    _claude_is_rate_limited "$log_file" 0 && _is_rl=1
                else
                    _claude_is_rate_limited "$log_file" 1 && _is_rl=1
                fi
                if [[ $_is_rl -eq 1 ]]; then
                    # 세션 로그에서 실제 리셋 시각 파싱 시도 (파싱 실패 시 기본 cooldown)
                    local _reset_ep=""
                    _reset_ep=$(_parse_reset_epoch "$log_file" 2>/dev/null) || true
                    if [[ -n "$_reset_ep" && "$_reset_ep" -gt "$_rl_now" ]]; then
                        entry_cooldown_epochs[$i]=$_reset_ep
                        local _wait_min=$(( (_reset_ep - _rl_now + 59) / 60 ))
                        if [[ -n "$model_suffix" ]]; then
                            printf '\\n\\033[33m⚠ %s (%s) rate-limit 감지. 리셋까지 약 %d분 대기\\033[0m\\n\\n' "$base_agent" "$model_suffix" "$_wait_min"
                        else
                            printf '\\n\\033[33m⚠ %s rate-limit 감지. 리셋까지 약 %d분 대기\\033[0m\\n\\n' "$base_agent" "$_wait_min"
                        fi
                    else
                        entry_cooldown_epochs[$i]=$((_rl_now + claude_retry_minutes * 60))
                        if [[ -n "$model_suffix" ]]; then
                            printf '\\n\\033[33m⚠ %s (%s) rate-limit 감지. %s분 후 재시도 예정\\033[0m\\n\\n' "$base_agent" "$model_suffix" "$claude_retry_minutes"
                        else
                            printf '\\n\\033[33m⚠ %s rate-limit 감지. %s분 후 재시도 예정\\033[0m\\n\\n' "$base_agent" "$claude_retry_minutes"
                        fi
                    fi
                    _save_cooldown_state
                    _reverse_handoff=0
                    exit_code=1  # rate limit → 강제 fallback
                    # 핸드오프 파일 생성: 다음 에이전트에게 컨텍스트 전달
                    _release_handoff
                    handoff_file=$(_create_handoff_file "$agent" "$log_file" "${{agent_args[@]}}")
                    printf '\\033[36m📋 핸드오프 컨텍스트 저장: %s\\033[0m\\n' "$handoff_file"
                else
                    entry_cooldown_epochs[$i]=0
                    _save_cooldown_state
                fi
            fi

            # 세션 로그 저장 (영구 디렉토리 설정 시)
            # agent:model 형식은 "agent-model"로 변환 (예: claude:sonnet → claude-sonnet)
            # plain "claude" 엔트리는 로그에서 실제 모델명을 파싱해 파일명에 반영
            _save_session_log "$log_file" "${{agent//:/-}}"

            # 비-Claude 에이전트 영구 로그 경로 보존 (reverse handoff용)
            local _perm_log_path=""
            if [[ "$base_agent" != "claude" && -n "$_fb_log_dir" ]]; then
                [[ -z "$_fallback_session_id" ]] && _fallback_session_id=$(_get_claude_session_id)
                local _non_claude_name="${{agent//:/-}}"
                _perm_log_path="${{_fb_log_dir}}/${{_fallback_session_id}}_${{_non_claude_name}}.log"
            fi

            # /exit 감지 (비-Claude 에이전트, 성공 종료 시)
            local _user_exited=0
            if [[ $exit_code -eq 0 && "$base_agent" != "claude" ]]; then
                _user_explicitly_exited "$log_file" && _user_exited=1
            fi

            rm -f "$log_file" "$rate_limit_marker"

            if [[ $exit_code -eq 0 ]]; then
                _release_handoff

                # 사용자가 /exit 명시적 종료 시 래퍼도 종료
                if [[ $_user_exited -eq 1 ]]; then
                    printf '\\033[36m👋 세션 종료\\033[0m\\n'
                    _restore_xtrace
                    return 0
                fi

                local now_epoch=$(date +%s)
                # 현재 에이전트가 claude가 아닌 경우, cooldown된 claude 엔트리 복귀 체크
                # _parse_agent_entry 호출 대신 직접 파싱하여 base_agent/model_suffix 오염 방지
                if [[ "$base_agent" != "claude" ]]; then
                    local _earliest_claude_idx=-1
                    local _any_claude_cooldown=0
                    for ((ci=0; ci<${{#agents[@]}}; ci++)); do
                        if [[ ${{entry_cooldown_epochs[$ci]}} -gt 0 ]]; then
                            local _ci_base="${{agents[$ci]%%:*}}"
                            if [[ "$_ci_base" == "claude" ]]; then
                                _any_claude_cooldown=1
                                if [[ $now_epoch -ge ${{entry_cooldown_epochs[$ci]}} ]]; then
                                    _earliest_claude_idx=$ci
                                    break
                                fi
                            fi
                        fi
                    done

                    if [[ $_earliest_claude_idx -ge 0 ]]; then
                        # Reverse handoff: non-Claude → Claude 컨텍스트 전달
                        if [[ -n "$_perm_log_path" && -f "$_perm_log_path" ]]; then
                            _release_handoff
                            handoff_file=$(_create_handoff_file "$agent" "$_perm_log_path" "${{agent_args[@]}}")
                            _reverse_handoff=1
                            printf '\\033[36m📋 핸드오프 컨텍스트 저장: %s\\033[0m\\n' "$handoff_file"
                        fi
                        printf '\\n\\033[36m🔁 Claude 제한 해제 감지. claude로 복귀합니다...\\033[0m\\n\\n'
                        start_idx=$_earliest_claude_idx
                        switched_back_to_claude=1
                        break
                    elif [[ $_any_claude_cooldown -eq 1 ]]; then
                        # 가장 빠른 복귀까지 남은 시간 계산
                        local _min_remain=999999
                        for ((ci=0; ci<${{#agents[@]}}; ci++)); do
                            if [[ ${{entry_cooldown_epochs[$ci]}} -gt $now_epoch ]]; then
                                local _ci_base="${{agents[$ci]%%:*}}"
                                if [[ "$_ci_base" == "claude" ]]; then
                                    local _r=$(( (entry_cooldown_epochs[$ci] - now_epoch + 59) / 60 ))
                                    [[ $_r -lt $_min_remain ]] && _min_remain=$_r
                                fi
                            fi
                        done
                        printf '\\n\\033[36m🔄 %s 세션 종료. Claude 복귀까지 약 %d분 남음. %s 재시작...\\033[0m\\n\\n' "$agent" "$_min_remain" "$agent"
                        start_idx=$i
                        switched_back_to_claude=1
                        break
                    fi
                fi
                _restore_xtrace
                return 0
            fi

            printf '\\n\\033[33m⚠ %s 종료 (code: %d). 다음 에이전트로 전환...\\033[0m\\n\\n' "$agent" "$exit_code"
        done

        if [[ $switched_back_to_claude -eq 1 ]]; then
            continue
        fi

        if [[ $tried -eq 0 ]]; then
            # cooldown 중인 엔트리가 있는지 확인
            local _any_pending=0
            local _min_wait=0
            local _expired_idx=-1
            local now_epoch=$(date +%s)
            for ((ci=0; ci<${{#agents[@]}}; ci++)); do
                if [[ ${{entry_cooldown_epochs[$ci]}} -gt 0 ]]; then
                    local _w=$((entry_cooldown_epochs[$ci] - now_epoch))
                    if [[ $_w -le 0 ]]; then
                        _expired_idx=$ci
                        break
                    else
                        _any_pending=1
                        [[ $_min_wait -eq 0 || $_w -lt $_min_wait ]] && _min_wait=$_w
                    fi
                fi
            done
            if [[ $_expired_idx -ge 0 ]]; then
                start_idx=$_expired_idx
                continue
            elif [[ $_any_pending -eq 1 && $_min_wait -gt 0 ]]; then
                printf '\\033[33m⏳ Claude 제한 해제 대기 중... %d초 후 재시도\\033[0m\\n' "$_min_wait"
                sleep "$_min_wait"
                start_idx=0
                continue
            fi
            printf '\\033[31m❌ 사용 가능한 AI 에이전트가 없습니다\\033[0m\\n'
            if [[ -z "$_fb_log_dir" && -n "$handoff_file" ]]; then
                rm -f "$handoff_file"
            fi
            _restore_xtrace
            return 1
        fi

        # 한 라운드가 끝났고 cooldown이 풀린 엔트리가 있다면 해당 엔트리부터 재시도
        local now_epoch=$(date +%s)
        for ((ci=0; ci<${{#agents[@]}}; ci++)); do
            if [[ ${{entry_cooldown_epochs[$ci]}} -gt 0 && $now_epoch -ge ${{entry_cooldown_epochs[$ci]}} ]]; then
                start_idx=$ci
                continue 2  # outer while loop
            fi
        done

        printf '\\033[31m❌ 모든 AI 에이전트 소진\\033[0m\\n'
        if [[ -z "$_fb_log_dir" && -n "$handoff_file" ]]; then
            rm -f "$handoff_file"
        fi
        _restore_xtrace
        return 1
    done
}}

# === Codex wrapper (skills sync) ===
# codex 직접 실행 시에도 팀 스킬 자동 동기화
codex() {{
    _ai_env_sync_skills
    command codex "$@"
}}"""
