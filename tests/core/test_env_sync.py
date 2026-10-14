"""비밀값 배포의 범위·백업·누락 방지를 검증한다."""

from pathlib import Path
from unittest.mock import patch

import pytest
from ai_env.core.env_sync import sync_env_files
from dotenv import dotenv_values


def test_env_sync_filters_backs_up_and_preserves_dry_run(tmp_path: Path) -> None:
    """팀별 key만 복사하고 기존 비밀 파일을 백업한다."""
    (tmp_path / ".env").write_text(
        "JIRA_TOKEN='private token'\nJIRA_EMAIL=test@example.com\nONLY_AI=private\n"
    )
    team = tmp_path / "cde-skills"
    team.mkdir()
    target = team / ".env"
    target.write_text("JIRA_TOKEN=old\n")
    catalog = {"JIRA_TOKEN": {"cde-skills:code"}}
    with patch("ai_env.core.env_sync.collect_team_env_keys", return_value=catalog):
        sync_env_files(tmp_path, dry_run=True)
        assert target.read_text() == "JIRA_TOKEN=old\n"
        assert not (tmp_path / ".env-backups").exists()
        sync_env_files(tmp_path)
        assert dotenv_values(target) == {
            "JIRA_TOKEN": "private token",
            "JIRA_EMAIL": "test@example.com",
        }
        assert target.stat().st_mode & 0o777 == 0o600
        backups = list((tmp_path / ".env-backups").glob("*.env"))
        assert len(backups) == 1
        assert backups[0].read_text() == "JIRA_TOKEN=old\n"
        assert backups[0].stat().st_mode & 0o777 == 0o600
        sync_env_files(tmp_path)
        assert list((tmp_path / ".env-backups").glob("*.env")) == backups


def test_env_sync_missing_value_prevents_all_writes(tmp_path: Path) -> None:
    """두 번째 대상의 누락을 발견해도 첫 번째 파일을 변경하지 않는다."""
    (tmp_path / ".env").write_text("FIRST=new\nSECOND=\n")
    for name, key in [("cde-skills", "FIRST"), ("cde-ranking-skills", "SECOND")]:
        (tmp_path / name).mkdir()
        (tmp_path / name / ".env").write_text(f"{key}=old\n")
    catalog = {"FIRST": {"cde-skills:code"}, "SECOND": {"cde-ranking-skills:code"}}
    with patch("ai_env.core.env_sync.collect_team_env_keys", return_value=catalog):
        with pytest.raises(ValueError, match="SECOND"):
            sync_env_files(tmp_path)
    assert (tmp_path / "cde-skills" / ".env").read_text() == "FIRST=old\n"
    assert (tmp_path / "cde-ranking-skills" / ".env").read_text() == "SECOND=old\n"
