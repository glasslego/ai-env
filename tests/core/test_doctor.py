"""doctor 모듈 테스트"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from ai_env.core.doctor import (
    CheckResult,
    DoctorReport,
    check_env,
    check_tools,
)


class TestCheckResult:
    def test_basic_creation(self) -> None:
        result = CheckResult("test", "pass", "ok", "env")
        assert result.name == "test"
        assert result.status == "pass"
        assert result.message == "ok"
        assert result.category == "env"


class TestDoctorReport:
    def test_empty_report(self) -> None:
        report = DoctorReport()
        assert report.passed == 0
        assert report.warned == 0
        assert report.failed == 0

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
        """설치된 도구는 pass"""
        report = DoctorReport()
        with patch("ai_env.core.doctor.shutil.which", return_value="/usr/local/bin/test"):
            check_tools(report)
        # claude, codex, gemini 3개 모두 검사
        assert len(report.checks) == 3
        assert all(c.status == "pass" for c in report.checks)

    def test_missing_tool(self) -> None:
        """설치되지 않은 도구는 warn"""
        report = DoctorReport()
        with patch("ai_env.core.doctor.shutil.which", return_value=None):
            check_tools(report)
        assert len(report.checks) == 3
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
        assert statuses["gemini"] == "warn"
