"""Core modules.

공개 심볼은 처음 사용할 때 import한다. hook처럼 일부 모듈만 쓰는 진입점이
설정·doctor 모듈까지 읽지 않게 한다.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .config import (
        MCPConfig,
        MCPServerConfig,
        OutputsConfig,
        ProviderConfig,
        Settings,
        expand_path,
        get_project_root,
        load_mcp_config,
        load_settings,
    )
    from .doctor import DoctorReport, run_doctor
    from .project_sync import ProjectSyncResult, sync_project_claude_to_codex
    from .secrets import SecretsManager, get_secrets_manager

_EXPORTS = {
    "MCPConfig": "config",
    "MCPServerConfig": "config",
    "OutputsConfig": "config",
    "ProviderConfig": "config",
    "Settings": "config",
    "expand_path": "config",
    "get_project_root": "config",
    "load_mcp_config": "config",
    "load_settings": "config",
    "DoctorReport": "doctor",
    "run_doctor": "doctor",
    "ProjectSyncResult": "project_sync",
    "sync_project_claude_to_codex": "project_sync",
    "SecretsManager": "secrets",
    "get_secrets_manager": "secrets",
}

__all__ = [
    "DoctorReport",
    "MCPConfig",
    "MCPServerConfig",
    "OutputsConfig",
    "ProjectSyncResult",
    "ProviderConfig",
    "SecretsManager",
    "Settings",
    "expand_path",
    "get_project_root",
    "get_secrets_manager",
    "load_mcp_config",
    "load_settings",
    "run_doctor",
    "sync_project_claude_to_codex",
]


def __getattr__(name: str) -> Any:  # noqa: ANN401 - 모듈 속성은 심볼마다 타입이 다르다.
    """요청한 공개 심볼만 해당 모듈에서 읽는다.

    Args:
        name: 공개 심볼 이름.

    Returns:
        해당 모듈의 객체.

    Raises:
        AttributeError: 공개 심볼이 아닐 때.
    """
    module = _EXPORTS.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(f".{module}", __name__), name)
