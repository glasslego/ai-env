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

    def __init__(self, secrets: SecretsManager):
        self.secrets = secrets
        self.mcp_config = load_mcp_config()
        self.settings = load_settings()

    def _substitute_env(self, value: str) -> str:
        """환경변수 치환"""
        return self.secrets.substitute(value)

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
                        env[key] = value
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

        for name, server in self.mcp_config.mcp_servers.items():
            if not server.enabled or "codex" not in server.targets:
                continue

            if server.type == "sse":
                url = self.secrets.get(server.url_env, "") if server.url_env else ""
                if url:
                    lines.append(f"[mcp_servers.{name}]")
                    lines.append(f'url = "{url}"')
                    lines.append("")
            else:
                lines.append(f"[mcp_servers.{name}]")
                lines.append(f'command = "{server.command}"')
                args_str = ", ".join(f'"{self._substitute_env(a)}"' for a in server.args)
                lines.append(f"args = [{args_str}]")

                if server.env_keys:
                    lines.append("")
                    lines.append(f"[mcp_servers.{name}.env]")
                    for key in server.env_keys:
                        value = self.secrets.get(key, "")
                        lines.append(f'{key} = "{value}"')
                lines.append("")

        return "\n".join(lines)

    def generate_gemini(self) -> dict[str, Any]:
        """Gemini CLI용 settings.local.json 생성"""
        servers = {}
        for name, server in self.mcp_config.mcp_servers.items():
            config = self._build_server_config(name, server, "gemini")
            if config:
                # Gemini는 type 필드 없이 url만
                if server.type == "sse":
                    servers[name] = {"url": config.get("url")}
                else:
                    servers[name] = config

        return {"security": {"auth": {"selectedType": "oauth-personal"}}, "mcpServers": servers}

    def generate_chatgpt_desktop(self) -> dict[str, Any]:
        """ChatGPT Desktop용 config 생성 (Claude Desktop과 동일한 포맷)"""
        return self.generate_claude_desktop()

    def _save_json_config(
        self, name: str, path_str: str, content: dict[str, Any], dry_run: bool
    ) -> Path:
        """JSON 설정 파일 저장 (공통 로직)"""
        path = expand_path(path_str)
        if not dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                json.dump(content, f, indent=2)
        return path

    def _save_text_config(self, name: str, path_str: str, content: str, dry_run: bool) -> Path:
        """텍스트 설정 파일 저장 (공통 로직)"""
        path = expand_path(path_str)
        if not dry_run:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
        return path

    def save_all(self, dry_run: bool = False) -> dict[str, Path]:
        """모든 설정 파일 저장"""
        results = {}

        # === Desktop 앱들 ===
        results["claude_desktop"] = self._save_json_config(
            "claude_desktop",
            self.settings.outputs.claude_desktop,
            self.generate_claude_desktop(),
            dry_run,
        )
        results["chatgpt_desktop"] = self._save_json_config(
            "chatgpt_desktop",
            self.settings.outputs.chatgpt_desktop,
            self.generate_chatgpt_desktop(),
            dry_run,
        )
        results["antigravity"] = self._save_json_config(
            "antigravity", self.settings.outputs.antigravity, self.generate_antigravity(), dry_run
        )

        # === CLI 도구들 (글로벌) ===
        results["claude_global"] = self._save_json_config(
            "claude_global",
            self.settings.outputs.claude_global,
            self.generate_claude_local(),
            dry_run,
        )
        results["codex_global"] = self._save_text_config(
            "codex_global", self.settings.outputs.codex_global, self.generate_codex(), dry_run
        )
        results["gemini_global"] = self._save_json_config(
            "gemini_global", self.settings.outputs.gemini_global, self.generate_gemini(), dry_run
        )

        # === 로컬 프로젝트 설정 ===
        results["claude_local"] = self._save_json_config(
            "claude_local",
            self.settings.outputs.claude_local,
            self.generate_claude_local(),
            dry_run,
        )
        results["codex_local"] = self._save_text_config(
            "codex_local", self.settings.outputs.codex_local, self.generate_codex(), dry_run
        )
        results["gemini_local"] = self._save_json_config(
            "gemini_local", self.settings.outputs.gemini_local, self.generate_gemini(), dry_run
        )

        # === 기타 ===
        results["shell_exports"] = self._save_text_config(
            "shell_exports",
            self.settings.outputs.shell_exports,
            self.secrets.export_to_shell(),
            dry_run,
        )

        return results
