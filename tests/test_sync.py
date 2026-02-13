"""Tests for sync logic."""

from unittest.mock import MagicMock, patch

import pytest
from ai_env.core.sync import (
    _collect_skill_sources,
    _sync_file_or_dir,
    _sync_skills_merged,
    sync_claude_global_config,
)


@pytest.fixture()
def mock_secrets_manager():
    """Mock secrets manager."""
    with patch("ai_env.core.sync.get_secrets_manager") as mock:
        manager = MagicMock()
        manager.list.return_value = {"API_KEY": "test_key"}
        manager.substitute.side_effect = lambda s: s.replace("${API_KEY}", "test_key")
        mock.return_value = manager
        yield mock


def test_sync_file_copy(tmp_path):
    """Test single file copy."""
    src = tmp_path / "source.txt"
    src.write_text("content")
    dst = tmp_path / "dest.txt"

    desc, count = _sync_file_or_dir(src, dst)

    assert count == 1
    assert dst.read_text() == "content"


def test_sync_directory_copy(tmp_path):
    """Test directory recursive copy."""
    src = tmp_path / "source"
    src.mkdir()
    (src / "file1.txt").write_text("1")
    (src / "subdir").mkdir()
    (src / "subdir" / "file2.txt").write_text("2")

    dst = tmp_path / "target"

    desc, count = _sync_file_or_dir(src, dst)

    assert count == 1  # 1 directory item
    assert (dst / "file1.txt").exists()
    assert (dst / "subdir" / "file2.txt").exists()


def test_sync_claude_global_config(tmp_path, mock_secrets_manager):
    """Test global config sync."""
    # Setup source structure
    project_root = tmp_path / "ai-env"
    source_dir = project_root / ".claude"
    global_dir = source_dir / "global"
    global_dir.mkdir(parents=True)

    (global_dir / "CLAUDE.md").write_text("# Claude Global")
    (global_dir / "settings.json.template").write_text('{"key": "${API_KEY}"}')

    target_dir = tmp_path / "home" / ".claude"

    with (
        patch("ai_env.core.sync.get_project_root", return_value=project_root),
        patch("pathlib.Path.home", return_value=tmp_path / "home"),
    ):
        results = sync_claude_global_config()

        assert "settings.json" in results

        # Verify substitution
        settings_dst = target_dir / "settings.json"
        assert settings_dst.exists()
        assert '{"key": "test_key"}' in settings_dst.read_text()


def test_collect_skill_sources_personal_only(tmp_path):
    """personal skills만 있을 때 수집."""
    project_root = tmp_path / "ai-env"
    skills_dir = project_root / ".claude" / "skills"

    # personal skills 생성
    (skills_dir / "git-worktree").mkdir(parents=True)
    (skills_dir / "git-worktree" / "SKILL.md").write_text("# git worktree")
    (skills_dir / "skill-creator").mkdir()
    (skills_dir / "skill-creator" / "SKILL.md").write_text("# creator")

    sources = _collect_skill_sources(project_root)
    names = [s.name for s in sources]

    assert len(sources) == 2
    assert "git-worktree" in names
    assert "skill-creator" in names


def test_collect_skill_sources_with_cde_skills(tmp_path):
    """personal + team(cde-skills symlink) 합쳐서 수집."""
    project_root = tmp_path / "ai-env"
    skills_dir = project_root / ".claude" / "skills"

    # personal skill
    (skills_dir / "git-worktree").mkdir(parents=True)
    (skills_dir / "git-worktree" / "SKILL.md").write_text("# git worktree")

    # cde-skills 실제 디렉토리 (symlink target)
    cde_real = tmp_path / "cde-skills-repo"
    cde_real.mkdir()
    (cde_real / "elasticsearch-query").mkdir()
    (cde_real / "elasticsearch-query" / "SKILL.md").write_text("# ES query")
    (cde_real / "spark-debug").mkdir()
    (cde_real / "spark-debug" / "SKILL.md").write_text("# Spark debug")
    # SKILL.md 없는 디렉토리는 무시
    (cde_real / "scripts").mkdir()
    (cde_real / "scripts" / "some_script.py").write_text("pass")

    # symlink 생성
    cde_link = project_root / "cde-skills"
    cde_link.symlink_to(cde_real)

    sources = _collect_skill_sources(project_root)
    names = [s.name for s in sources]

    assert len(sources) == 3
    assert "git-worktree" in names
    assert "elasticsearch-query" in names
    assert "spark-debug" in names
    assert "scripts" not in names


def test_sync_skills_merged(tmp_path):
    """personal + team 스킬이 대상 디렉토리에 합쳐지는지 확인."""
    project_root = tmp_path / "ai-env"
    skills_dir = project_root / ".claude" / "skills"

    # personal
    (skills_dir / "mcp-config").mkdir(parents=True)
    (skills_dir / "mcp-config" / "SKILL.md").write_text("# MCP config")

    # team (symlink)
    cde_real = tmp_path / "cde-skills-repo"
    (cde_real / "trino-analyst").mkdir(parents=True)
    (cde_real / "trino-analyst" / "SKILL.md").write_text("# Trino")
    (project_root / "cde-skills").symlink_to(cde_real)

    dst = tmp_path / "target-skills"
    desc, count = _sync_skills_merged(project_root, dst, dry_run=False)

    assert count == 2
    assert (dst / "mcp-config" / "SKILL.md").exists()
    assert (dst / "trino-analyst" / "SKILL.md").exists()


def _setup_multi_team_skills(tmp_path):
    """테스트용 multi-team skills 환경 생성 헬퍼."""
    project_root = tmp_path / "ai-env"
    skills_dir = project_root / ".claude" / "skills"

    # personal skill
    (skills_dir / "my-skill").mkdir(parents=True)
    (skills_dir / "my-skill" / "SKILL.md").write_text("# my skill")

    # cde-skills (team 1)
    cde1 = tmp_path / "cde-skills-repo"
    cde1.mkdir()
    (cde1 / "es-query").mkdir()
    (cde1 / "es-query" / "SKILL.md").write_text("# ES query")

    # cde-ranking-skills (team 2)
    cde2 = tmp_path / "cde-ranking-repo"
    cde2.mkdir()
    (cde2 / "ranking-lookup").mkdir()
    (cde2 / "ranking-lookup" / "SKILL.md").write_text("# ranking")
    (cde2 / "score-drilldown").mkdir()
    (cde2 / "score-drilldown" / "SKILL.md").write_text("# score")

    # symlinks
    (project_root / "cde-skills").symlink_to(cde1)
    (project_root / "cde-ranking-skills").symlink_to(cde2)

    return project_root


def test_collect_skills_include(tmp_path):
    """--skills-include로 특정 팀 스킬만 포함."""
    project_root = _setup_multi_team_skills(tmp_path)

    sources = _collect_skill_sources(project_root, skills_include=["cde-skills"])
    names = [s.name for s in sources]

    assert "my-skill" in names  # personal은 항상 포함
    assert "es-query" in names  # cde-skills 포함
    assert "ranking-lookup" not in names  # cde-ranking-skills 제외
    assert "score-drilldown" not in names


def test_collect_skills_exclude(tmp_path):
    """--skills-exclude로 특정 팀 스킬 제외."""
    project_root = _setup_multi_team_skills(tmp_path)

    sources = _collect_skill_sources(project_root, skills_exclude=["cde-ranking-skills"])
    names = [s.name for s in sources]

    assert "my-skill" in names  # personal은 항상 포함
    assert "es-query" in names  # cde-skills 포함
    assert "ranking-lookup" not in names  # cde-ranking-skills 제외
    assert "score-drilldown" not in names


def test_collect_skills_no_filter(tmp_path):
    """필터 없으면 전체 포함."""
    project_root = _setup_multi_team_skills(tmp_path)

    sources = _collect_skill_sources(project_root)
    names = [s.name for s in sources]

    assert len(names) == 4  # 1 personal + 1 cde-skills + 2 cde-ranking-skills
    assert "my-skill" in names
    assert "es-query" in names
    assert "ranking-lookup" in names
    assert "score-drilldown" in names
