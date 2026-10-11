"""`.env.example` 자동 생성 — mcp_servers.yaml + settings.yaml 기반"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from .config import get_project_root, load_mcp_config, load_settings


def collect_team_env_keys(project_root: Path) -> dict[str, set[str]]:
    """팀 템플릿과 실행 코드에서 변수 이름만 수집한다.

    Args:
        project_root: cde-*skills 연결이 있는 ai-env 루트.

    Returns:
        변수 이름별 출처 집합. 실제 값은 읽거나 반환하지 않는다.
    """
    keys: dict[str, set[str]] = {}
    if (project_root / "cde-skills").is_dir():
        keys.update(
            {
                "CDE_SKILLS_SOURCE_ROOT": {"cde-skills:runtime"},
                "CDE_SKILLS_REPO_ROOT": {"cde-skills:runtime"},
            }
        )
    layouts = {
        "cde-skills": (
            "plugins/cde-skills/skills",
            "plugins/cde-skills/skills/_shared/env.template",
        ),
        "cde-ranking-skills": (".claude/skills", ".env.sample"),
    }
    for name, (skills_path, template_path) in layouts.items():
        repo = project_root / name
        template = repo / template_path
        if template.is_file():
            for key in re.findall(
                r"^\s*(?:#\s*)?([A-Z][A-Z0-9_]+)\s*=", template.read_text(), re.MULTILINE
            ):
                keys.setdefault(key, set()).add(f"{name}:template")
        for root in (repo / skills_path, repo / "lib"):
            if not root.is_dir():
                continue
            for script in root.rglob("*.py"):
                if script.name.startswith("test_") or "tests" in script.parts:
                    continue
                try:
                    tree = ast.parse(script.read_text(encoding="utf-8"))
                except (SyntaxError, UnicodeError):
                    continue
                for node in ast.walk(tree):
                    key_node = None
                    if isinstance(node, ast.Call) and node.args:
                        if ast.unparse(node.func) in {"os.getenv", "os.environ.get", "getenv"}:
                            key_node = node.args[0]
                    elif (
                        isinstance(node, ast.Subscript) and ast.unparse(node.value) == "os.environ"
                    ):
                        key_node = node.slice
                    if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                        key = key_node.value
                        if re.fullmatch(r"[A-Z][A-Z0-9_]+", key) and key not in {
                            "USER",
                            "HOME",
                            "PATH",
                            "APPDATA",
                            "XDG_CACHE_HOME",
                        }:
                            keys.setdefault(key, set()).add(f"{name}:code")
    return keys


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
        if provider.env_key:
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

    # 3. Extra credentials (mcp/providers 외부에서 코드가 직접 읽는 키)
    if settings.extra_env_keys:
        lines.append("# === Extra Credentials ===")
        provider_and_mcp_keys = provider_key_set | set(mcp_keys.keys()) | set(mcp_url_keys.keys())
        for entry in settings.extra_env_keys:
            if entry.key in provider_and_mcp_keys:
                continue  # 중복 제거
            if entry.description:
                lines.append(f"# {entry.description}")
            lines.append(f"{entry.key}=")
        lines.append("")

    # 팀 변수는 선택 기능과 fallback을 포함한다. 빈 활성 값으로 기본값을 가리지 않는다.
    existing_keys = provider_key_set | set(mcp_keys) | set(mcp_url_keys)
    existing_keys.update(entry.key for entry in settings.extra_env_keys)
    team_keys = collect_team_env_keys(get_project_root())
    if team_keys:
        lines.extend(
            [
                "# === Team skills (필요한 기능만 주석 해제 후 설정) ===",
                "# 모든 항목이 필수는 아님. 인증은 각 스킬의 Vault/환경변수 fallback을 따릅니다.",
                "# 템플릿의 예시 비밀번호·토큰은 복사하지 않습니다.",
            ]
        )
        for key in sorted(team_keys.keys() - existing_keys):
            lines.append(f"# Used by: {', '.join(sorted(team_keys[key]))}")
            lines.append(f"# {key}=")
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
