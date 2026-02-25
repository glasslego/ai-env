"""설정 관리 모듈"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel, Field

_T = TypeVar("_T", bound=BaseModel)


class ProviderConfig(BaseModel):
    """AI Provider 설정"""

    enabled: bool = True
    env_key: str = ""


class OutputsConfig(BaseModel):
    """출력 경로 설정"""

    # Desktop 앱들
    claude_desktop: str = "~/Library/Application Support/Claude/claude_desktop_config.json"
    chatgpt_desktop: str = "~/Library/Application Support/ChatGPT/config.json"
    codex_desktop: str = "~/.codex/codex.config.json"
    antigravity: str = "~/.gemini/antigravity/mcp_config.json"

    # CLI 도구들 (글로벌)
    claude_global: str = "~/.claude/settings.json"
    codex_global: str = "~/.codex/config.toml"
    gemini_global: str = "~/.gemini/settings.json"

    # 로컬 프로젝트 설정 (glocal = global template for local)
    claude_local: str = "./.claude/settings.glocal.json"
    codex_local: str = "./.codex/config.toml"
    gemini_local: str = "./.gemini/settings.local.json"

    # 기타
    shell_exports: str = "./generated/shell_exports.sh"


class Settings(BaseModel):
    """메인 설정"""

    version: str = "1.0"
    default_agent: str = "claude"
    env_file: str = ".env"
    codex_model: str = "gpt-5.3-codex"
    codex_model_reasoning_effort: str = "high"
    agent_priority: list[str] = Field(default_factory=lambda: ["claude", "codex"])
    fallback_log_dir: str | None = None
    providers: dict[str, ProviderConfig] = Field(default_factory=dict)
    outputs: OutputsConfig = Field(default_factory=OutputsConfig)


class MCPServerConfig(BaseModel):
    """MCP 서버 설정"""

    enabled: bool = True
    type: str = "stdio"  # stdio or sse
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env_keys: list[str] = Field(default_factory=list)
    url_env: str | None = None  # SSE 서버용
    targets: list[str] = Field(default_factory=list)
    startup_timeout_sec: int | None = None  # Codex MCP startup timeout (seconds)


class MCPConfig(BaseModel):
    """MCP 설정"""

    mcp_servers: dict[str, MCPServerConfig] = Field(default_factory=dict)


def get_project_root() -> Path:
    """프로젝트 루트 경로 반환"""
    return Path(__file__).parent.parent.parent.parent


def _load_yaml_model(model_cls: type[_T], config_path: Path, label: str) -> _T:
    """YAML 파일을 Pydantic 모델로 로드하는 공통 함수

    Args:
        model_cls: Pydantic 모델 클래스
        config_path: YAML 파일 경로
        label: 에러 메시지용 라벨

    Returns:
        로드된 모델 인스턴스

    Raises:
        ValueError: YAML 파싱 오류 또는 검증 실패 시
    """
    if not config_path.exists():
        return model_cls()

    try:
        with open(config_path) as f:
            data = yaml.safe_load(f)
        if data is None:
            return model_cls()
        return model_cls(**data)
    except yaml.YAMLError as e:
        raise ValueError(f"Failed to parse YAML file {config_path}: {e}") from e
    except Exception as e:
        raise ValueError(f"Failed to load {label} from {config_path}: {e}") from e


def load_settings(config_path: Path | None = None) -> Settings:
    """설정 파일 로드

    Args:
        config_path: 설정 파일 경로 (None이면 기본 경로 사용)

    Returns:
        로드된 Settings 객체

    Raises:
        ValueError: YAML 파싱 오류 또는 설정 검증 실패 시
    """
    if config_path is None:
        config_path = get_project_root() / "config" / "settings.yaml"
    return _load_yaml_model(Settings, config_path, "settings")


def load_mcp_config(config_path: Path | None = None) -> MCPConfig:
    """MCP 설정 파일 로드

    Args:
        config_path: 설정 파일 경로 (None이면 기본 경로 사용)

    Returns:
        로드된 MCPConfig 객체

    Raises:
        ValueError: YAML 파싱 오류 또는 설정 검증 실패 시
    """
    if config_path is None:
        config_path = get_project_root() / "config" / "mcp_servers.yaml"
    return _load_yaml_model(MCPConfig, config_path, "MCP config")


def expand_path(path: str) -> Path:
    """경로 확장 (~, 환경변수 등)

    Args:
        path: 확장할 경로 문자열 (예: "~/config", "$HOME/data")

    Returns:
        확장된 절대 경로

    Example:
        >>> expand_path("~/.config")
        Path('/Users/username/.config')
    """
    return Path(os.path.expandvars(os.path.expanduser(path)))
