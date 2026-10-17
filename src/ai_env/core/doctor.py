"""환경 건강 검사 모듈"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from dotenv import dotenv_values

from .config import expand_path, get_project_root, load_settings
from .env_sync import ATLASSIAN_ENV_KEYS
from .secrets import get_secrets_manager


@dataclass
class CheckResult:
    """단일 검사 결과"""

    name: str
    status: str  # "pass", "warn", "fail"
    message: str
    category: str  # "env", "tools", "sync", "shell"


@dataclass
class DoctorReport:
    """전체 검사 보고서"""

    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.status == "pass")

    @property
    def warned(self) -> int:
        return sum(1 for c in self.checks if c.status == "warn")

    @property
    def failed(self) -> int:
        return sum(1 for c in self.checks if c.status == "fail")

    def to_dict(self) -> dict[str, Any]:
        """JSON 출력용 딕셔너리 변환"""
        return {
            "checks": [
                {
                    "name": c.name,
                    "status": c.status,
                    "message": c.message,
                    "category": c.category,
                }
                for c in self.checks
            ],
            "summary": {
                "passed": self.passed,
                "warned": self.warned,
                "failed": self.failed,
            },
        }


def _sha256(content: str) -> str:
    """문자열의 SHA-256 해시 반환"""
    return hashlib.sha256(content.encode()).hexdigest()


def check_env(report: DoctorReport) -> None:
    """환경변수 검사"""
    project_root = get_project_root()
    env_file = project_root / ".env"

    if env_file.exists():
        report.checks.append(CheckResult(".env file", "pass", "exists", "env"))
    else:
        report.checks.append(CheckResult(".env file", "fail", "not found", "env"))
        return

    settings = load_settings()
    sm = get_secrets_manager()

    for _name, provider in settings.providers.items():
        if not provider.enabled or not provider.env_key:
            continue
        value = sm.get(provider.env_key)
        if value:
            report.checks.append(CheckResult(provider.env_key, "pass", "configured", "env"))
        else:
            report.checks.append(CheckResult(provider.env_key, "warn", "not set", "env"))


def check_tools(report: DoctorReport) -> None:
    """CLI 도구 설치 검사 (SPEC-013: claude + codex만)"""
    tools = ["claude", "codex"]
    for tool in tools:
        path = shutil.which(tool)
        if path:
            report.checks.append(CheckResult(tool, "pass", f"installed ({path})", "tools"))
        else:
            report.checks.append(CheckResult(tool, "warn", "not found", "tools"))


def check_skill_auth(report: DoctorReport) -> None:
    """Jira·Wiki 인증 설정과 배포 상태를 값 노출 없이 검사한다.

    Args:
        report: 검사 결과를 추가할 보고서. 네트워크 인증 검사는 수행하지 않는다.
    """
    root = get_project_root()
    source = root / ".env"
    if not source.is_file():
        return
    values = dotenv_values(source, interpolate=False)
    if not any(key.startswith(("JIRA_", "WIKI_")) for key in values):
        return
    jira_url = values.get("JIRA_URL") or ""
    try:
        cloud = (urlparse(jira_url).hostname or "").endswith(".atlassian.net")
        wiki_cloud = (urlparse(values.get("WIKI_BASE_URL") or jira_url).hostname or "").endswith(
            ".atlassian.net"
        )
    except ValueError:
        cloud = wiki_cloud = False
    jira_required = ["JIRA_URL", "JIRA_TOKEN"] + (["JIRA_EMAIL"] if cloud else [])
    missing = [key for key in jira_required if not values.get(key)]
    report.checks.append(
        CheckResult(
            "Jira auth",
            "fail" if missing else "pass",
            f"missing: {', '.join(missing)}"
            if missing
            else "configured (authentication not checked)",
            "env",
        )
    )
    wiki_missing = []
    if not values.get("WIKI_BASE_URL") and not (cloud and jira_url):
        wiki_missing.append("WIKI_BASE_URL")
    if not values.get("WIKI_TOKEN") and not (wiki_cloud and values.get("JIRA_TOKEN")):
        wiki_missing.append("WIKI_TOKEN (or JIRA_TOKEN for Cloud)")
    if wiki_cloud and not (values.get("WIKI_EMAIL") or values.get("JIRA_EMAIL")):
        wiki_missing.append("WIKI_EMAIL or JIRA_EMAIL")
    report.checks.append(
        CheckResult(
            "Wiki auth",
            "fail" if wiki_missing else "pass",
            f"missing: {', '.join(wiki_missing)}"
            if wiki_missing
            else "configured (authentication not checked)",
            "env",
        )
    )
    keys = {
        key for key in values if key.startswith(("JIRA_", "WIKI_", "CDE_SKILLS_"))
    } | ATLASSIAN_ENV_KEYS
    targets = [Path.home() / ".cde-skills.env"]
    targets.extend(
        root / name / ".env"
        for name in ("cde-skills", "cde-ranking-skills")
        if (root / name).is_dir()
    )
    for target in targets:
        if not target.is_file():
            report.checks.append(
                CheckResult(str(target), "fail", "not deployed (run 'ai-env sync-env')", "env")
            )
            continue
        deployed = dotenv_values(target, interpolate=False)
        drift = sorted(key for key in keys if (values.get(key) or "") != (deployed.get(key) or ""))
        status = "fail" if drift else "pass"
        message = f"out of sync: {', '.join(drift)}" if drift else "Jira/Wiki auth matches source"
        if target.stat().st_mode & 0o077:
            status = "warn" if not drift else "fail"
            message += "; expected permissions 600"
        report.checks.append(CheckResult(str(target), status, message, "env"))


def check_sync_drift(report: DoctorReport) -> None:
    """동기화 드리프트 검사

    현재 생성 결과와 실제 파일을 비교하여 drift를 감지한다.
    """
    sm = get_secrets_manager()

    # MCP 설정 파일 드리프트 검사
    # 지연 임포트: core.__init__ → doctor → mcp.generator → core 순환 방지
    from ..mcp import MCPConfigGenerator

    generator = MCPConfigGenerator(sm)
    settings = generator.settings

    # codex_global/codex_local은 동일한 config.toml을 공유하므로 한 번만 생성
    codex_content = generator.generate_codex()

    # (타겟 이름, 생성 함수, 출력 경로) 튜플 리스트 (Claude+Codex 전용)
    mcp_targets: list[tuple[str, Any, str]] = [
        ("claude_desktop", generator.generate_claude_desktop(), settings.outputs.claude_desktop),
        ("codex_desktop", generator.generate_codex_desktop(), settings.outputs.codex_desktop),
        ("codex_global", codex_content, settings.outputs.codex_global),
        ("claude_local", generator.generate_claude_local(), settings.outputs.claude_local),
        ("codex_local", codex_content, settings.outputs.codex_local),
    ]

    for name, content, path_str in mcp_targets:
        path = expand_path(path_str)
        if not path.exists():
            report.checks.append(CheckResult(name, "warn", f"not found: {path}", "sync"))
            continue

        # 생성 결과를 문자열로 변환
        if isinstance(content, dict):
            expected = json.dumps(content, indent=2)
        else:
            expected = content

        actual = path.read_text()
        if _sha256(expected) == _sha256(actual):
            report.checks.append(CheckResult(name, "pass", "up to date", "sync"))
        else:
            report.checks.append(CheckResult(name, "fail", f"drifted: {path}", "sync"))

    # Claude 글로벌 설정 파일 존재 검사
    target_dir = Path.home() / ".claude"

    claude_items = [
        ("~/.claude/CLAUDE.md", target_dir / "CLAUDE.md"),
        ("~/.claude/commands/", target_dir / "commands"),
        ("~/.claude/skills/", target_dir / "skills"),
    ]

    for name, dst in claude_items:
        if dst.exists():
            report.checks.append(CheckResult(name, "pass", "exists", "sync"))
        else:
            report.checks.append(CheckResult(name, "warn", "not found", "sync"))

    # Codex AGENTS.md
    instruction_items = [
        ("~/.codex/AGENTS.md", Path.home() / ".codex" / "AGENTS.md"),
        ("~/.codex/skills/", Path.home() / ".codex" / "skills"),
    ]

    for name, dst in instruction_items:
        if dst.exists():
            report.checks.append(CheckResult(name, "pass", "exists", "sync"))
        else:
            report.checks.append(CheckResult(name, "warn", "not found", "sync"))


def check_shell(report: DoctorReport) -> None:
    """쉘 설정 검사"""
    settings = load_settings()
    shell_path = expand_path(settings.outputs.shell_exports)

    if shell_path.exists():
        report.checks.append(CheckResult("shell_exports.sh", "pass", "exists", "shell"))
    else:
        report.checks.append(
            CheckResult("shell_exports.sh", "fail", "not found (run 'ai-env sync')", "shell")
        )


def run_doctor() -> DoctorReport:
    """전체 건강 검사 실행"""
    report = DoctorReport()

    check_env(report)
    check_skill_auth(report)
    check_tools(report)
    check_sync_drift(report)
    check_shell(report)

    return report
