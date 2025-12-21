"""설정 관리 모듈"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class ProviderConfig(BaseModel):
    """AI Provider 설정"""

    enabled: bool = True
    env_key: str = ""
    config_dir: str = ""
    auth_type: str = "api_key"
    uses_gemini_auth: bool = False


class OutputsConfig(BaseModel):
    """출력 경로 설정"""

    # Desktop 앱들
    claude_desktop: str = "~/Library/Application Support/Claude/claude_desktop_config.json"
    chatgpt_desktop: str = "~/Library/Application Support/ChatGPT/config.json"
    antigravity: str = "~/.gemini/antigravity/mcp_config.json"

    # CLI 도구들 (글로벌)
    claude_global: str = "~/.claude/settings.json"
    codex_global: str = "~/.codex/config.toml"
    gemini_global: str = "~/.gemini/settings.json"

    # 로컬 프로젝트 설정
    claude_local: str = "./.claude/settings.local.json"
    codex_local: str = "./.codex/config.toml"
    gemini_local: str = "./.gemini/settings.local.json"

    # 기타
    shell_exports: str = "./generated/shell_exports.sh"


class Settings(BaseModel):
    """메인 설정"""

    version: str = "1.0"
    default_agent: str = "claude"
    env_file: str = ".env"
    providers: dict[str, ProviderConfig] = Field(default_factory=dict)
    outputs: OutputsConfig = Field(default_factory=OutputsConfig)
    sync_targets: list[str] = Field(default_factory=list)


class MCPServerConfig(BaseModel):
    """MCP 서버 설정"""

    enabled: bool = True
    type: str = "stdio"  # stdio or sse
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env_keys: list[str] = Field(default_factory=list)
    url_env: str | None = None  # SSE 서버용
    targets: list[str] = Field(default_factory=list)


class MCPConfig(BaseModel):
    """MCP 설정"""

    mcp_servers: dict[str, MCPServerConfig] = Field(default_factory=dict)


def get_project_root() -> Path:
    """프로젝트 루트 경로 반환"""
    return Path(__file__).parent.parent.parent.parent


def load_settings(config_path: Path | None = None) -> Settings:
    """설정 파일 로드"""
    if config_path is None:
        config_path = get_project_root() / "config" / "settings.yaml"

    if not config_path.exists():
        return Settings()

    with open(config_path) as f:
        data = yaml.safe_load(f)

    return Settings(**data)


def load_mcp_config(config_path: Path | None = None) -> MCPConfig:
    """MCP 설정 파일 로드"""
    if config_path is None:
        config_path = get_project_root() / "config" / "mcp_servers.yaml"

    if not config_path.exists():
        return MCPConfig()

    with open(config_path) as f:
        data = yaml.safe_load(f)

    return MCPConfig(**data)


def expand_path(path: str) -> Path:
    """경로 확장 (~, 환경변수 등)"""
    return Path(os.path.expandvars(os.path.expanduser(path)))
