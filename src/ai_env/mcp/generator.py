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
            return {"type": "sse", "url": url}

        else:
            # STDIO 서버 (Docker, npx 등)
            config: dict[str, Any] = {
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
        lines = [
            'trust_level = "trusted"',
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
            else:
                lines.append(f'command = "{config["command"]}"')
                args_str = ", ".join(f'"{a}"' for a in config["args"])
                lines.append(f"args = [{args_str}]")

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
            # 기타
            ("shell_exports", self.settings.outputs.shell_exports, self.secrets.export_to_shell()),
        ]

        return {
            name: self._save_config(name, path, content, dry_run) for name, path, content in configs
        }
