"""doctor 모듈 테스트"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from ai_env.core.doctor import (
    CheckResult,
    DoctorReport,
    check_env,
    check_skill_auth,
    check_sync_drift,
    check_tools,
)
from ai_env.core.env_sync import sync_env_files
from ai_env.mcp import MCPConfigGenerator


def test_skill_auth_reports_missing_email_and_portable_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """마스터 토큰만 있어도 이메일·플러그인용 배포 누락을 감지한다."""
    (tmp_path / ".env").write_text("JIRA_URL=https://example.atlassian.net\nJIRA_TOKEN=secret\n")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    with patch("ai_env.core.doctor.get_project_root", return_value=tmp_path):
        report = DoctorReport()
        check_skill_auth(report)
    by_name = {check.name: check for check in report.checks}
    assert by_name["Jira auth"].status == "fail"
    assert "JIRA_EMAIL" in by_name["Jira auth"].message
    assert by_name[str(tmp_path / ".cde-skills.env")].status == "fail"
    assert "secret" not in str(report.to_dict())


def test_sync_drift_ignores_codex_app_managed_sections(tmp_path: Path) -> None:
    """Codex 앱이 추가한 섹션은 sync가 보존하므로 drift로 판정하지 않는다."""
    generated = '[mcp_servers.fetch]\ncommand = "uvx"\n'
    codex_path = tmp_path / "config.toml"

    class FakeGenerator(MCPConfigGenerator):
        def __init__(self, _sm: object) -> None:
            outputs = type("Outputs", (), {})()
            for name in ("claude_desktop", "codex_desktop", "claude_local", "codex_local"):
                setattr(outputs, name, str(tmp_path / f"missing_{name}"))
            outputs.codex_global = str(codex_path)
            self.settings = type("Settings", (), {"outputs": outputs})()

        def generate_codex(self) -> str:
            return generated

        def generate_claude_desktop(self) -> dict:
            return {}

        generate_codex_desktop = generate_claude_desktop
        generate_claude_local = generate_claude_desktop

    def run_check() -> str:
        report = DoctorReport()
        with patch("ai_env.mcp.MCPConfigGenerator", FakeGenerator):
            check_sync_drift(report)
        return next(c.status for c in report.checks if c.name == "codex_global")

    codex_path.write_text(generated + '\n[projects."/tmp/x"]\ntrust_level = "trusted"\n')
    assert run_check() == "pass"

    codex_path.write_text('[mcp_servers.fetch]\ncommand = "old"\n')
    assert run_check() == "fail"


def test_skill_auth_fallback_and_stale_wiki_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """배포 후 Jira fallback을 인정하고 잘못된 Wiki override가 되살아나면 실패한다."""
    (tmp_path / ".env").write_text(
        "JIRA_URL=https://example.atlassian.net\nJIRA_EMAIL=test@example.com\n"
        "JIRA_TOKEN=secret\nWIKI_TOKEN=\n"
    )
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    with patch("ai_env.core.env_sync.collect_team_env_keys", return_value={}):
        sync_env_files(tmp_path)
    with patch("ai_env.core.doctor.get_project_root", return_value=tmp_path):
        report = DoctorReport()
        check_skill_auth(report)
        assert report.failed == 0
        assert all(check.status == "pass" for check in report.checks)
        portable = tmp_path / ".cde-skills.env"
        portable.write_text(portable.read_text().replace("WIKI_TOKEN=", "WIKI_TOKEN=obsolete"))
        report = DoctorReport()
        check_skill_auth(report)
    failed = [check for check in report.checks if check.status == "fail"]
    assert len(failed) == 1
    assert "WIKI_TOKEN" in failed[0].message
    assert "obsolete" not in str(report.to_dict())


class TestDoctorReport:
    def test_counts(self) -> None:
        report = DoctorReport(
            checks=[
                CheckResult("a", "pass", "ok", "env"),
                CheckResult("b", "pass", "ok", "env"),
                CheckResult("c", "warn", "missing", "env"),
                CheckResult("d", "fail", "error", "tools"),
            ]
        )
        assert report.passed == 2
        assert report.warned == 1
        assert report.failed == 1

    def test_to_dict(self) -> None:
        report = DoctorReport(
            checks=[
                CheckResult("x", "pass", "ok", "env"),
                CheckResult("y", "fail", "bad", "sync"),
            ]
        )
        d = report.to_dict()
        assert len(d["checks"]) == 2
        assert d["summary"]["passed"] == 1
        assert d["summary"]["failed"] == 1
        assert d["summary"]["warned"] == 0
        assert d["checks"][0]["name"] == "x"
        assert d["checks"][1]["status"] == "fail"


class TestCheckEnv:
    def test_env_file_missing(self, tmp_path: Path) -> None:
        """환경변수 파일이 없으면 fail"""
        report = DoctorReport()
        with patch("ai_env.core.doctor.get_project_root", return_value=tmp_path):
            check_env(report)
        assert len(report.checks) == 1
        assert report.checks[0].status == "fail"
        assert report.checks[0].name == ".env file"

    def test_env_file_exists_no_providers(self, tmp_path: Path) -> None:
        """환경변수 파일이 있고 프로바이더가 없으면 pass"""
        (tmp_path / ".env").write_text("FOO=bar\n")
        # 빈 settings.yaml 생성
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "settings.yaml").write_text("version: '1.0'\nproviders: {}\n")

        report = DoctorReport()
        with patch("ai_env.core.doctor.get_project_root", return_value=tmp_path):
            check_env(report)
        assert report.checks[0].status == "pass"
        assert report.checks[0].name == ".env file"


class TestCheckTools:
    def test_installed_tool(self) -> None:
        """설치된 도구는 pass (SPEC-013: claude + codex)"""
        report = DoctorReport()
        with patch("ai_env.core.doctor.shutil.which", return_value="/usr/local/bin/test"):
            check_tools(report)
        assert len(report.checks) == 2
        assert all(c.status == "pass" for c in report.checks)

    def test_missing_tool(self) -> None:
        """설치되지 않은 도구는 warn"""
        report = DoctorReport()
        with patch("ai_env.core.doctor.shutil.which", return_value=None):
            check_tools(report)
        assert len(report.checks) == 2
        assert all(c.status == "warn" for c in report.checks)

    def test_partial_installation(self) -> None:
        """일부만 설치된 경우"""
        report = DoctorReport()

        def mock_which(tool: str) -> str | None:
            return "/usr/local/bin/claude" if tool == "claude" else None

        with patch("ai_env.core.doctor.shutil.which", side_effect=mock_which):
            check_tools(report)
        statuses = {c.name: c.status for c in report.checks}
        assert statuses["claude"] == "pass"
        assert statuses["codex"] == "warn"
