"""MCP 설정 생성기"""

from __future__ import annotations

import json
import warnings
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
    # 파괴적 삭제 명령 deny 목록 (rm -rf, hdfs dfs -rm -r 등).
    # HDFS 삭제는 어떤 형태로도 절대 허용하지 않는다 (-rm -r/-rm -rf/-rm -r -f/-rmr 모두 차단).
    RM_RF_DENY_RULES = [
        "Bash(rm -rf /)",
        "Bash(rm -rf /*)",
        "Bash(rm -rf ~)",
        "Bash(rm -rf ~/*)",
        "Bash(hdfs dfs -rm -r:*)",
        "Bash(hdfs dfs -rm -rf:*)",
        "Bash(hdfs dfs -rm -r -f:*)",
        "Bash(hdfs dfs -rmr:*)",
    ]
    CLAUDE_PERMISSION_ALLOW = [
        "Bash(*)",
        "WebSearch",
        "WebFetch",
        "mcp__*",
    ]
    # 환경변수 키 매핑 (프로바이더별 키 이름 차이 흡수)
    ENV_KEY_MAPPING = {
        "GITHUB_GLASSLEGO_TOKEN": "GITHUB_PERSONAL_ACCESS_TOKEN",
        "GITHUB_TOKEN": "GITHUB_PERSONAL_ACCESS_TOKEN",
        "AGIT_TOKEN": "AGIT_ACCESS_TOKEN",
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

        if server.type in ("sse", "http"):
            url = self.secrets.get(server.url_env, "") if server.url_env else ""
            if not url:
                return None
            config: dict[str, Any] = {"type": server.type, "url": url}

        else:
            config = {
                "command": server.command,
                "args": [self._substitute_env(arg) for arg in server.args],
            }

            if server.env_keys:
                env = {}
                seen_mapped: dict[str, str] = {}
                for key in server.env_keys:
                    value = self.secrets.get(key, "")
                    if value:
                        mapped_key = self._map_env_key(key)
                        if mapped_key in seen_mapped and seen_mapped[mapped_key] != key:
                            warnings.warn(
                                f"MCP server '{name}': env keys '{seen_mapped[mapped_key]}' and "
                                f"'{key}' both map to '{mapped_key}'. "
                                f"Last value (from '{key}') will be used.",
                                stacklevel=2,
                            )
                        seen_mapped[mapped_key] = key
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

    def generate_claude_user_mcp_servers(self) -> dict[str, Any]:
        """Claude Code user scope(~/.claude.json top-level mcpServers)용 서버 dict 생성.

        Claude Code는 settings.json의 mcpServers 키를 읽지 않는다. MCP 정의는
        ~/.claude.json(user/local scope) 또는 .mcp.json(project scope)에서만
        로드되므로, sync는 이 dict를 ~/.claude.json top-level에 기록한다.
        mcp_servers.yaml의 claude_local 타겟을 그대로 재사용한다.
        """
        return self._generate_mcp_servers_for_target("claude_local")

    def generate_codex(self) -> str:
        """Codex CLI용 config.toml 생성."""
        lines = [
            f'model = "{self.settings.codex_model}"',
            f'model_reasoning_effort = "{self.settings.codex_model_reasoning_effort}"',
            "",
        ]

        for name, config in self._generate_mcp_servers_for_target("codex").items():
            lines.extend(self._codex_server_block(name, config))

        return "\n".join(lines)

    @staticmethod
    def _split_toml_sections(text: str) -> tuple[list[str], dict[str, list[str]], list[str]]:
        """TOML을 top-level 라인과 section 블록으로 느슨하게 분리."""
        preamble: list[str] = []
        sections: dict[str, list[str]] = {}
        order: list[str] = []
        current: str | None = None

        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                current = stripped.strip("[]")
                sections[current] = [line]
                order.append(current)
                continue

            if current is None:
                preamble.append(line)
            else:
                sections[current].append(line)

        return preamble, sections, order

    @staticmethod
    def _toml_key(line: str) -> str | None:
        """단일 라인 TOML key=value의 key 추출."""
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            return None
        return stripped.split("=", 1)[0].strip()

    @classmethod
    def _merge_key_lines(cls, existing: list[str], generated: list[str]) -> list[str]:
        """generated의 key=value 라인을 existing에 덮어쓰되 다른 라인은 보존."""
        generated_by_key = {
            key: line for line in generated if (key := cls._toml_key(line)) is not None
        }
        if not generated_by_key:
            return existing

        merged: list[str] = []
        written: set[str] = set()

        for line in existing:
            key = cls._toml_key(line)
            if key in generated_by_key:
                merged.append(generated_by_key[key])
                written.add(key)
            else:
                merged.append(line)

        for key, line in generated_by_key.items():
            if key not in written:
                merged.append(line)

        return merged

    @staticmethod
    def _codex_mcp_server_name(section_name: str) -> str | None:
        """mcp_servers.<name> 또는 mcp_servers.<name>.env 섹션의 name 추출."""
        prefix = "mcp_servers."
        if not section_name.startswith(prefix):
            return None
        rest = section_name[len(prefix) :]
        if rest.endswith(".env"):
            rest = rest[: -len(".env")]
        return rest or None

    @classmethod
    def merge_codex_config(cls, existing: str, generated: str) -> str:
        """기존 Codex config.toml에 ai-env 관리 블록만 병합.

        Codex Desktop/CLI가 직접 관리하는 plugins, marketplaces, desktop,
        project trust, node_repl 같은 섹션을 보존하면서 ai-env가 생성하는
        모델, env, features.rmcp_client, MCP 서버 설정만 갱신한다.
        """
        if not existing.strip():
            return generated

        existing_pre, existing_sections, existing_order = cls._split_toml_sections(existing)
        generated_pre, generated_sections, generated_order = cls._split_toml_sections(generated)

        generated_mcp_names = {
            name
            for section in generated_sections
            if (name := cls._codex_mcp_server_name(section)) is not None
        }
        generated_mcp_sections = [
            section
            for section in generated_order
            if cls._codex_mcp_server_name(section) in generated_mcp_names
        ]

        merged_lines = cls._merge_key_lines(existing_pre, generated_pre)

        for section in ("env", "features"):
            if section not in generated_sections:
                continue
            if merged_lines and merged_lines[-1] != "":
                merged_lines.append("")
            existing_block = existing_sections.get(section, [f"[{section}]"])
            merged_lines.extend(cls._merge_key_lines(existing_block, generated_sections[section]))

        if merged_lines and merged_lines[-1] != "":
            merged_lines.append("")

        for section in generated_mcp_sections:
            merged_lines.extend(generated_sections[section])

        for section in existing_order:
            if section in {"env", "features"}:
                continue
            server_name = cls._codex_mcp_server_name(section)
            if server_name in generated_mcp_names:
                continue
            if merged_lines and merged_lines[-1] != "":
                merged_lines.append("")
            merged_lines.extend(existing_sections[section])

        return "\n".join(merged_lines).rstrip() + "\n"

    @staticmethod
    def _codex_server_block(name: str, config: dict[str, Any]) -> list[str]:
        """Codex config.toml의 단일 [mcp_servers.<name>] 블록을 라인 리스트로 직렬화."""
        lines: list[str] = [f"[mcp_servers.{name}]"]

        server_type = config.get("type")
        is_url_based = server_type in ("sse", "http")
        if is_url_based:
            lines.append(f'type = "{server_type}"')
            lines.append(f'url = "{config["url"]}"')
        else:
            lines.append(f'command = "{config["command"]}"')
            args_str = ", ".join(f'"{a}"' for a in config["args"])
            lines.append(f"args = [{args_str}]")

        if "startup_timeout_sec" in config:
            lines.append(f"startup_timeout_sec = {config['startup_timeout_sec']}")

        # stdio 서버 전용: 추가 환경변수 서브 테이블
        if not is_url_based and "env" in config:
            lines.append("")
            lines.append(f"[mcp_servers.{name}.env]")
            for key, value in config["env"].items():
                lines.append(f'{key} = "{value}"')

        lines.append("")
        return lines

    def generate_codex_desktop(self) -> dict[str, Any]:
        """Codex Desktop App용 codex.config.json 생성

        Codex Desktop은 ~/.codex/codex.config.json을 읽으며,
        SSE 서버는 url 필드만, stdio 서버는 command/args/env로 구성됩니다.
        """
        servers = self._generate_mcp_servers_for_target("codex_desktop")

        # Codex Desktop JSON 형식: URL 기반(sse/http)은 url만, type 필드 제거
        for name, config in servers.items():
            if config.get("type") in ("sse", "http"):
                servers[name] = {"url": config["url"]}

        return {"autoAcceptTools": True, "mcpServers": servers}

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
                if name == "codex_global" and isinstance(content, str) and path.exists():
                    content = self.merge_codex_config(path.read_text(), content)
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
        """Claude Code + Codex 설정 파일 저장 (SPEC-013)."""
        codex_config = self.generate_codex()

        configs: list[tuple[str, str, Any]] = [
            (
                "claude_desktop",
                self.settings.outputs.claude_desktop,
                self.generate_claude_desktop(),
            ),
            (
                "codex_desktop",
                self.settings.outputs.codex_desktop,
                self.generate_codex_desktop(),
            ),
            ("codex_global", self.settings.outputs.codex_global, codex_config),
            ("claude_local", self.settings.outputs.claude_local, self.generate_claude_local()),
            ("codex_local", self.settings.outputs.codex_local, codex_config),
            (
                "shell_exports",
                self.settings.outputs.shell_exports,
                self.secrets.export_to_shell() + "\n\n" + self.generate_shell_functions(),
            ),
        ]

        return {
            name: self._save_config(name, path, content, dry_run) for name, path, content in configs
        }
