"""환경 건강 검사 모듈"""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import expand_path, get_project_root, load_settings
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


def _file_sha256(path: Path) -> str:
    """파일의 SHA-256 해시 반환"""
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
    """CLI 도구 설치 검사"""
    tools = ["claude", "codex", "gemini"]
    for tool in tools:
        path = shutil.which(tool)
        if path:
            report.checks.append(CheckResult(tool, "pass", f"installed ({path})", "tools"))
        else:
            report.checks.append(CheckResult(tool, "warn", "not found", "tools"))


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

    # (타겟 이름, 생성 함수, 출력 경로) 튜플 리스트
    mcp_targets: list[tuple[str, Any, str]] = [
        ("claude_desktop", generator.generate_claude_desktop(), settings.outputs.claude_desktop),
        ("chatgpt_desktop", generator.generate_chatgpt_desktop(), settings.outputs.chatgpt_desktop),
        ("codex_desktop", generator.generate_codex_desktop(), settings.outputs.codex_desktop),
        ("antigravity", generator.generate_antigravity(), settings.outputs.antigravity),
        ("codex_global", generator.generate_codex(), settings.outputs.codex_global),
        ("gemini_global", generator.generate_gemini(), settings.outputs.gemini_global),
        ("claude_local", generator.generate_claude_local(), settings.outputs.claude_local),
        ("codex_local", generator.generate_codex(), settings.outputs.codex_local),
        ("gemini_local", generator.generate_gemini(), settings.outputs.gemini_local),
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
    project_root = get_project_root()
    global_dir = project_root / ".claude" / "global"
    target_dir = Path.home() / ".claude"

    claude_items = [
        ("~/.claude/CLAUDE.md", global_dir / "CLAUDE.md", target_dir / "CLAUDE.md"),
        ("~/.claude/commands/", project_root / ".claude" / "commands", target_dir / "commands"),
        ("~/.claude/skills/", target_dir / "skills", target_dir / "skills"),
    ]

    for name, _src, dst in claude_items:
        if dst.exists():
            report.checks.append(CheckResult(name, "pass", "exists", "sync"))
        else:
            report.checks.append(CheckResult(name, "warn", "not found", "sync"))

    # Codex AGENTS.md / Gemini GEMINI.md
    instruction_items = [
        ("~/.codex/AGENTS.md", Path.home() / ".codex" / "AGENTS.md"),
        ("~/.gemini/GEMINI.md", Path.home() / ".gemini" / "GEMINI.md"),
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
    check_tools(report)
    check_sync_drift(report)
    check_shell(report)

    return report
