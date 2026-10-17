"""비밀값 배포의 범위·백업·누락 방지를 검증한다."""

from pathlib import Path
from unittest.mock import patch

import pytest
from ai_env.core.env_sync import sync_env_files
from dotenv import dotenv_values


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """테스트가 실제 사용자 인증 fallback을 쓰지 않도록 격리한다."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)


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


def test_global_fallback_without_team_checkout_preserves_other_credentials(tmp_path: Path) -> None:
    """플러그인만 설치해도 공통 fallback을 읽으며 관련 없는 비밀값은 보존한다."""
    (tmp_path / ".env").write_text(
        "JIRA_TOKEN='current token'\nJIRA_EMAIL=test@example.com\nONLY_AI=private\n"
    )
    target = Path.home() / ".cde-skills.env"
    target.write_text("JIRA_TOKEN=old\nOTHER_SERVICE=keep\n")
    with patch("ai_env.core.env_sync.collect_team_env_keys", return_value={}):
        assert sync_env_files(tmp_path, dry_run=True) == [target]
        assert dotenv_values(target)["JIRA_TOKEN"] == "old"
        sync_env_files(tmp_path)
    assert dotenv_values(target) == {
        "JIRA_TOKEN": "current token",
        "JIRA_EMAIL": "test@example.com",
        "OTHER_SERVICE": "keep",
    }
    assert target.stat().st_mode & 0o777 == 0o600


def test_explicit_wiki_token_clear_uses_same_cloud_jira_credentials(tmp_path: Path) -> None:
    """명시적으로 비운 Wiki 토큰은 같은 Cloud의 정상 Jira 인증으로 대체할 수 있다."""
    (tmp_path / ".env").write_text(
        "JIRA_URL=https://example.atlassian.net\nJIRA_EMAIL=test@example.com\n"
        "JIRA_TOKEN=current\nWIKI_BASE_URL=https://example.atlassian.net/wiki\nWIKI_TOKEN=\n"
    )
    team = tmp_path / "cde-skills"
    team.mkdir()
    (team / ".env").write_text("WIKI_TOKEN=obsolete\n")
    with patch("ai_env.core.env_sync.collect_team_env_keys", return_value={}):
        sync_env_files(tmp_path)
    for target in [team / ".env", Path.home() / ".cde-skills.env"]:
        values = dotenv_values(target)
        assert values["WIKI_TOKEN"] == ""
        assert (values.get("WIKI_TOKEN") or values.get("JIRA_TOKEN")) == "current"


@pytest.mark.parametrize("jira_url", ["https://legacy.example.com", "https://other.atlassian.net"])
def test_cannot_clear_wiki_token_for_different_or_legacy_site(
    tmp_path: Path, jira_url: str
) -> None:
    """다른 사이트의 Jira 토큰으로 Wiki 인증이 가능하다고 가정하지 않는다."""
    (tmp_path / ".env").write_text(
        f"JIRA_URL={jira_url}\nJIRA_EMAIL=test@example.com\nJIRA_TOKEN=current\n"
        "WIKI_BASE_URL=https://example.atlassian.net/wiki\nWIKI_TOKEN=\n"
    )
    team = tmp_path / "cde-skills"
    team.mkdir()
    (team / ".env").write_text("WIKI_TOKEN=keep\n")
    with patch("ai_env.core.env_sync.collect_team_env_keys", return_value={}):
        with pytest.raises(ValueError, match="WIKI_TOKEN"):
            sync_env_files(tmp_path)
    assert (team / ".env").read_text() == "WIKI_TOKEN=keep\n"
    assert not (Path.home() / ".cde-skills.env").exists()
