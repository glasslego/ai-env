"""MCP 설정 생성기"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..core import (
    MCPServerConfig,
    SecretsManager,
    expand_path,
    load_mcp_config,
    load_settings,
)


class MCPConfigGenerator:
    """MCP 설정 파일 생성기"""

    CODEX_DEFAULT_STARTUP_TIMEOUT_SEC = 30
    CODEX_PERMISSION_ALLOW = [
        "Read(*)",
        "Edit(**)",
        "Bash(git:*)",
        "Bash(npm:*)",
        "Bash(*)",
        "WebFetch(*)",
        "mcp__*",
        "WebSearch",
        "mcp__ide__getDiagnostics",
    ]
    CODEX_PERMISSION_DENY = [
        "Bash(sudo:*)",
        "Bash(rm -rf /)",
        "Bash(rm -rf /*)",
        "Bash(rm -rf ~)",
        "Bash(rm -rf ~/*)",
        "Bash(mkfs*)",
        "Bash(dd if=*of=/dev/*)",
        "Bash(chmod -R 777 /)",
        "Bash(chown -R * /)",
        "Bash(shutdown*)",
        "Bash(reboot*)",
        "Bash(init 0*)",
        "Bash(git push * --force)",
        "Bash(git clean -fdx /)",
        "Bash(DROP DATABASE*)",
        "Bash(DROP TABLE*)",
    ]
    CODEX_PERMISSION_ENV = {"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"}
    CODEX_TEAMMATE_MODE = "tmux"

    # 환경변수 키 매핑 (프로바이더별 키 이름 차이 흡수)
    ENV_KEY_MAPPING = {
        "GITHUB_GLASSLEGO_TOKEN": "GITHUB_PERSONAL_ACCESS_TOKEN",
        "GITHUB_KAKAO_TOKEN": "GITHUB_PERSONAL_ACCESS_TOKEN",
    }

    def __init__(self, secrets: SecretsManager):
        self.secrets = secrets
        self.mcp_config = load_mcp_config()
        self.settings = load_settings()

    def _substitute_env(self, value: str) -> str:
        """환경변수 치환"""
        return self.secrets.substitute(value)

    def _map_env_key(self, key: str) -> str:
        """환경변수 키를 타겟별 키로 매핑

        일부 MCP 서버는 다른 키 이름을 요구함 (예: GitHub MCP)

        Args:
            key: 원본 환경변수 키

        Returns:
            매핑된 환경변수 키
        """
        return self.ENV_KEY_MAPPING.get(key, key)

    def _build_server_config(
        self, name: str, server: MCPServerConfig, target: str
    ) -> dict[str, Any] | None:
        """단일 MCP 서버 설정 생성"""
        if not server.enabled:
            return None

        if target not in server.targets:
            return None

        if server.type == "sse":
            # SSE 서버
            url = self.secrets.get(server.url_env, "") if server.url_env else ""
            if not url:
                return None
            config: dict[str, Any] = {"type": "sse", "url": url}

        else:
            # STDIO 서버 (Docker, npx 등)
            config = {
                "command": server.command,
                "args": [self._substitute_env(arg) for arg in server.args],
            }

            # 환경변수가 필요한 경우
            if server.env_keys:
                env = {}
                for key in server.env_keys:
                    value = self.secrets.get(key, "")
                    if value:
                        mapped_key = self._map_env_key(key)
                        env[mapped_key] = value
                if env:
                    config["env"] = env

        # Codex는 서버 기동 타임아웃을 server-level로 설정 가능
        if target == "codex":
            timeout = (
                server.startup_timeout_sec
                if server.startup_timeout_sec is not None
                else self.CODEX_DEFAULT_STARTUP_TIMEOUT_SEC
            )
            config["startup_timeout_sec"] = timeout

        return config

    def _generate_mcp_servers_for_target(self, target: str) -> dict[str, Any]:
        """특정 타겟용 MCP 서버 설정 생성 (공통 로직)"""
        servers = {}
        for name, server in self.mcp_config.mcp_servers.items():
            config = self._build_server_config(name, server, target)
            if config:
                servers[name] = config
        return servers

    def generate_claude_desktop(self) -> dict[str, Any]:
        """Claude Desktop용 config 생성"""
        return {"mcpServers": self._generate_mcp_servers_for_target("claude_desktop")}

    def generate_antigravity(self) -> dict[str, Any]:
        """Antigravity용 config 생성"""
        return {"mcpServers": self._generate_mcp_servers_for_target("antigravity")}

    def generate_claude_local(self) -> dict[str, Any]:
        """Claude Code 로컬 프로젝트용 settings.local.json 생성"""
        return {
            "permissions": {"allow": [], "deny": [], "ask": [], "defaultMode": "acceptEdits"},
            "mcpServers": self._generate_mcp_servers_for_target("claude_local"),
        }

    def generate_codex(self) -> str:
        """Codex용 config.toml 생성"""
        allow_str = ", ".join(f'"{item}"' for item in self.CODEX_PERMISSION_ALLOW)
        deny_str = ", ".join(f'"{item}"' for item in self.CODEX_PERMISSION_DENY)
        lines = [
            'trust_level = "trusted"',
            'approval_policy = "never"',
            'sandbox_mode = "danger-full-access"',
            "",
            "[permissions]",
            f"allow = [{allow_str}]",
            f"deny = [{deny_str}]",
            f'teammateMode = "{self.CODEX_TEAMMATE_MODE}"',
            "",
            "[permissions.env]",
            *[f'{key} = "{value}"' for key, value in self.CODEX_PERMISSION_ENV.items()],
            "",
            "[features]",
            "rmcp_client = true",
            "",
        ]

        servers = self._generate_mcp_servers_for_target("codex")
        for name, config in servers.items():
            lines.append(f"[mcp_servers.{name}]")

            if config.get("type") == "sse":
                lines.append('type = "sse"')
                lines.append(f'url = "{config["url"]}"')
                if "startup_timeout_sec" in config:
                    lines.append(f'startup_timeout_sec = {config["startup_timeout_sec"]}')
            else:
                lines.append(f'command = "{config["command"]}"')
                args_str = ", ".join(f'"{a}"' for a in config["args"])
                lines.append(f"args = [{args_str}]")
                if "startup_timeout_sec" in config:
                    lines.append(f'startup_timeout_sec = {config["startup_timeout_sec"]}')

                if "env" in config:
                    lines.append("")
                    lines.append(f"[mcp_servers.{name}.env]")
                    for key, value in config["env"].items():
                        lines.append(f'{key} = "{value}"')

            lines.append("")

        return "\n".join(lines)

    def generate_gemini(self) -> dict[str, Any]:
        """Gemini CLI용 settings.json 생성"""
        servers = self._generate_mcp_servers_for_target("gemini")

        # Gemini CLI: SSE 서버는 type 필드 없이 url만 사용
        for name, config in servers.items():
            if config.get("type") == "sse":
                servers[name] = {"url": config["url"]}

        return {"security": {"auth": {"selectedType": "oauth-personal"}}, "mcpServers": servers}

    def generate_chatgpt_desktop(self) -> dict[str, Any]:
        """ChatGPT Desktop용 config 생성"""
        return {"mcpServers": self._generate_mcp_servers_for_target("chatgpt_desktop")}

    def generate_shell_functions(self) -> str:
        """에이전트 우선순위 기반 vibe 쉘 함수 생성

        settings.yaml의 agent_priority 순서대로 AI 에이전트를 시도하는
        'vibe' 쉘 함수를 생성합니다. 앞 순위 에이전트가 비정상 종료(세션 한도 등)하면
        다음 에이전트로 자동 전환되며, Claude rate-limit 해제 후 자동 복귀를 시도합니다.

        Returns:
            bash 함수 문자열
        """
        agents = self.settings.agent_priority
        if not agents:
            return ""

        agents_str = " ".join(f'"{a}"' for a in agents)
        priority_display = " → ".join(agents)

        return f"""\
# === AI Agent Fallback (vibe coding) ===
# Priority: {priority_display}
# Usage: vibe [prompt]  - 우선순위대로 에이전트 시도, 실패 시 자동 전환
#        vibe -2        - 2순위 에이전트부터 시작 (예: codex)
#        vibe -l        - 에이전트 우선순위 목록 출력
# Env:   VIBE_CLAUDE_RETRY_MINUTES (default: 15)
vibe() {{
    local agents=({agents_str})
    local start_idx=0
    local prompt=""
    local claude_retry_epoch=0
    local claude_retry_minutes="${{VIBE_CLAUDE_RETRY_MINUTES:-15}}"

    _vibe_is_rate_limited() {{
        local log_file="$1"
        grep -Eiq \
            "rate limit|usage limit|quota|too many requests|try again in|credit balance|token limit|exceeded" \
            "$log_file"
    }}

    # 옵션 파싱
    case "$1" in
        -l|--list)
            printf '\\033[36mAgent priority:\\033[0m\\n'
            for i in "${{!agents[@]}}"; do
                printf '  %d. %s\\n' "$((i+1))" "${{agents[$i]}}"
            done
            return 0
            ;;
        -[0-9])
            start_idx=$((${{1#-}} - 1))
            shift
            ;;
    esac
    prompt="$*"

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
            log_file=$(mktemp -t "vibe-${{agent}}.XXXXXX")

            if [[ -n "$prompt" ]]; then
                "$agent" "$prompt" > >(tee "$log_file") 2>&1
            else
                "$agent" > >(tee "$log_file") 2>&1
            fi
            local exit_code=$?

            if [[ "$agent" == "claude" ]]; then
                if [[ $exit_code -ne 0 ]] && _vibe_is_rate_limited "$log_file"; then
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

    def _save_config(
        self, name: str, path_str: str, content: dict[str, Any] | str, dry_run: bool
    ) -> Path:
        """설정 파일 저장 (JSON 또는 텍스트)

        Args:
            name: 설정 이름
            path_str: 저장 경로 문자열
            content: 저장할 데이터 (dict/list면 JSON, str이면 텍스트)
            dry_run: True면 실제 저장하지 않음

        Returns:
            저장 경로

        Raises:
            OSError: 파일 쓰기 오류
            PermissionError: 권한 오류
        """
        path = expand_path(path_str)
        if not dry_run:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "w") as f:
                    if isinstance(content, dict | list):
                        json.dump(content, f, indent=2)
                    else:
                        f.write(content)
            except PermissionError as e:
                raise PermissionError(f"Permission denied writing {name} to {path}") from e
            except OSError as e:
                raise OSError(f"Failed to write {name} to {path}: {e}") from e
        return path

    def save_all(self, dry_run: bool = False) -> dict[str, Path]:
        """모든 설정 파일 저장

        Args:
            dry_run: True면 실제 저장하지 않고 경로만 반환

        Returns:
            {설정이름: 저장경로} 딕셔너리
        """
        # 설정 목록: (이름, 경로, 콘텐츠)
        # dict/list는 JSON으로, str은 텍스트로 자동 저장
        configs: list[tuple[str, str, Any]] = [
            # Desktop 앱들
            (
                "claude_desktop",
                self.settings.outputs.claude_desktop,
                self.generate_claude_desktop(),
            ),
            (
                "chatgpt_desktop",
                self.settings.outputs.chatgpt_desktop,
                self.generate_chatgpt_desktop(),
            ),
            ("antigravity", self.settings.outputs.antigravity, self.generate_antigravity()),
            # CLI 도구들 (글로벌)
            # claude_global은 sync_claude_global_config()에서 template 기반으로 생성
            # (permissions 포함), 여기서 덮어쓰지 않음
            ("codex_global", self.settings.outputs.codex_global, self.generate_codex()),
            ("gemini_global", self.settings.outputs.gemini_global, self.generate_gemini()),
            # 로컬 프로젝트 설정
            ("claude_local", self.settings.outputs.claude_local, self.generate_claude_local()),
            ("codex_local", self.settings.outputs.codex_local, self.generate_codex()),
            ("gemini_local", self.settings.outputs.gemini_local, self.generate_gemini()),
            # 기타 (shell exports + vibe 함수)
            (
                "shell_exports",
                self.settings.outputs.shell_exports,
                self.secrets.export_to_shell() + "\n\n" + self.generate_shell_functions(),
            ),
        ]

        return {
            name: self._save_config(name, path, content, dry_run) for name, path, content in configs
        }
