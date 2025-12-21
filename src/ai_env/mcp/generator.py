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
from .vibe import generate_shell_functions


class MCPConfigGenerator:
    """MCP 설정 파일 생성기"""

    CODEX_DEFAULT_STARTUP_TIMEOUT_SEC = 30
    RM_RF_DENY_RULES = [
        "Bash(rm -rf /)",
        "Bash(rm -rf /*)",
        "Bash(rm -rf ~)",
        "Bash(rm -rf ~/*)",
    ]
    CLAUDE_PERMISSION_ALLOW = [
        "Bash(*)",
        "WebSearch",
        "WebFetch",
        "mcp__*",
    ]
    CODEX_PERMISSION_ALLOW = [
        "Read(*)",
        "Edit(**)",
        "Bash(git:*)",
        "Bash(npm:*)",
        "Bash(*)",
        "WebFetch(*)",
        "mcp__*",
        "WebSearch",
    ]
    CODEX_PERMISSION_DENY = RM_RF_DENY_RULES
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
        """환경변수 키를 타겟별 키로 매핑"""
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
            url = self.secrets.get(server.url_env, "") if server.url_env else ""
            if not url:
                return None
            config: dict[str, Any] = {"type": "sse", "url": url}

        else:
            config = {
                "command": server.command,
                "args": [self._substitute_env(arg) for arg in server.args],
            }

            if server.env_keys:
                env = {}
                for key in server.env_keys:
                    value = self.secrets.get(key, "")
                    if value:
                        mapped_key = self._map_env_key(key)
                        env[mapped_key] = value
                if env:
                    config["env"] = env

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
            "permissions": {
                "allow": self.CLAUDE_PERMISSION_ALLOW,
                "deny": self.RM_RF_DENY_RULES,
                "ask": [],
                "defaultMode": "acceptEdits",
            },
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
            f'model = "{self.settings.codex_model}"',
            f'model_reasoning_effort = "{self.settings.codex_model_reasoning_effort}"',
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
                    lines.append(f"startup_timeout_sec = {config['startup_timeout_sec']}")
            else:
                lines.append(f'command = "{config["command"]}"')
                args_str = ", ".join(f'"{a}"' for a in config["args"])
                lines.append(f"args = [{args_str}]")
                if "startup_timeout_sec" in config:
                    lines.append(f"startup_timeout_sec = {config['startup_timeout_sec']}")

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

        for name, config in servers.items():
            if config.get("type") == "sse":
                servers[name] = {"url": config["url"]}

        return {"security": {"auth": {"selectedType": "oauth-personal"}}, "mcpServers": servers}

    def generate_codex_desktop(self) -> dict[str, Any]:
        """Codex Desktop App용 codex.config.json 생성

        Codex Desktop은 ~/.codex/codex.config.json을 읽으며,
        SSE 서버는 url 필드만, stdio 서버는 command/args/env로 구성됩니다.
        """
        servers = self._generate_mcp_servers_for_target("codex_desktop")

        # Codex Desktop JSON 형식: SSE는 url만, type 필드 제거
        for name, config in servers.items():
            if config.get("type") == "sse":
                servers[name] = {"url": config["url"]}
            # startup_timeout_sec는 codex CLI 전용이므로 제거
            config.pop("startup_timeout_sec", None)

        return {"autoAcceptTools": True, "mcpServers": servers}

    def generate_chatgpt_desktop(self) -> dict[str, Any]:
        """ChatGPT Desktop용 config 생성"""
        return {"mcpServers": self._generate_mcp_servers_for_target("chatgpt_desktop")}

    def generate_shell_functions(self) -> str:
        """에이전트 우선순위 기반 vibe 쉘 함수 생성 (vibe 모듈에 위임)"""
        return generate_shell_functions(
            self.settings.agent_priority,
            fallback_log_dir=self.settings.fallback_log_dir,
        )

    def _save_config(
        self, name: str, path_str: str, content: dict[str, Any] | str, dry_run: bool
    ) -> Path:
        """설정 파일 저장 (JSON 또는 텍스트)"""
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
        """모든 설정 파일 저장"""
        codex_config = self.generate_codex()
        gemini_config = self.generate_gemini()

        configs: list[tuple[str, str, Any]] = [
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
            (
                "codex_desktop",
                self.settings.outputs.codex_desktop,
                self.generate_codex_desktop(),
            ),
            ("antigravity", self.settings.outputs.antigravity, self.generate_antigravity()),
            ("codex_global", self.settings.outputs.codex_global, codex_config),
            ("gemini_global", self.settings.outputs.gemini_global, gemini_config),
            ("claude_local", self.settings.outputs.claude_local, self.generate_claude_local()),
            ("codex_local", self.settings.outputs.codex_local, codex_config),
            ("gemini_local", self.settings.outputs.gemini_local, gemini_config),
            (
                "shell_exports",
                self.settings.outputs.shell_exports,
                self.secrets.export_to_shell() + "\n\n" + self.generate_shell_functions(),
            ),
        ]

        return {
            name: self._save_config(name, path, content, dry_run) for name, path, content in configs
        }
