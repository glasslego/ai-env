"""`.env.example` 자동 생성 — mcp_servers.yaml + settings.yaml 기반"""

from __future__ import annotations

from .config import get_project_root, load_mcp_config, load_settings


def generate_env_example() -> str:
    """mcp_servers.yaml과 settings.yaml에서 필요한 환경변수를 수집하여 .env.example 생성

    Returns:
        .env.example 파일 내용 문자열
    """
    settings = load_settings()
    mcp_config = load_mcp_config()

    lines: list[str] = [
        "# ai-env 환경변수 설정",
        "# 이 파일을 .env로 복사한 뒤 실제 값을 입력하세요:",
        "#   cp .env.example .env",
        "",
    ]

    # 1. Provider API 키
    provider_keys: list[tuple[str, str]] = []
    for name, provider in settings.providers.items():
        if hasattr(provider, "env_key") and provider.env_key:
            provider_keys.append((provider.env_key, f"{name} API"))

    if provider_keys:
        lines.append("# === AI Provider API Keys ===")
        for key, desc in provider_keys:
            lines.append(f"# {desc}")
            lines.append(f"{key}=")
        lines.append("")

    # 2. MCP 서버 env_keys
    mcp_keys: dict[str, list[str]] = {}  # key → [서버 이름들]
    mcp_url_keys: dict[str, list[str]] = {}  # url_env → [서버 이름들]

    for name, server in mcp_config.mcp_servers.items():
        if not server.enabled:
            continue
        for key in server.env_keys:
            mcp_keys.setdefault(key, []).append(name)
        if server.url_env:
            mcp_url_keys.setdefault(server.url_env, []).append(name)

    # Provider 키와 중복 제거
    provider_key_set = {k for k, _ in provider_keys}

    if mcp_keys or mcp_url_keys:
        lines.append("# === MCP Server Credentials ===")

        for key in sorted(mcp_keys.keys()):
            if key in provider_key_set:
                continue
            servers = ", ".join(mcp_keys[key])
            lines.append(f"# Used by: {servers}")
            lines.append(f"{key}=")

        for key in sorted(mcp_url_keys.keys()):
            if key in provider_key_set:
                continue
            servers = ", ".join(mcp_url_keys[key])
            lines.append(f"# SSE URL for: {servers}")
            lines.append(f"{key}=")

        lines.append("")

    lines.append("# === Optional ===")
    lines.append("# CLAUDE_FALLBACK_LOG_DIR=.claude/logs")
    lines.append("# CLAUDE_FALLBACK_RETRY_MINUTES=15")
    lines.append("")

    return "\n".join(lines)


def save_env_example(dry_run: bool = False) -> str | None:
    """프로젝트 루트에 .env.example 생성

    Args:
        dry_run: True면 실제 저장하지 않음

    Returns:
        생성된 파일 경로 (또는 None)
    """
    project_root = get_project_root()
    content = generate_env_example()
    path = project_root / ".env.example"

    if not dry_run:
        path.write_text(content, encoding="utf-8")

    return str(path)
