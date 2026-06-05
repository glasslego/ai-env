"""Tests for sync logic."""

import json
import stat
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from ai_env.core.sync import (
    _build_skills_index,
    _collect_skill_sources,
    _extract_skill_summary,
    _sync_file_or_dir,
    _sync_skills_merged,
    safe_copy_skill_tree,
    sync_claude_global_config,
    sync_codex_global_config,
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


def test_sync_claude_global_config_writes_profile_settings(tmp_path, mock_secrets_manager):
    """Claude 설정 동기화 시 enterprise/personal 프로필 파일도 생성."""
    project_root = tmp_path / "ai-env"
    source_dir = project_root / ".claude"
    global_dir = source_dir / "global"
    global_dir.mkdir(parents=True)

    (global_dir / "CLAUDE.md").write_text("# Claude Global")
    (global_dir / "settings.json.template").write_text(
        '{"model": "enterprise", "key": "${API_KEY}"}'
    )
    (global_dir / "settings.personal.json.template").write_text(
        '{"model": "personal", "key": "${API_KEY}"}'
    )

    home_dir = tmp_path / "home"
    target_dir = home_dir / ".claude"
    personal_dir = home_dir / ".claude-personal"

    with (
        patch("ai_env.core.sync.get_project_root", return_value=project_root),
        patch("pathlib.Path.home", return_value=home_dir),
    ):
        results = sync_claude_global_config()

    assert "settings.json" in results
    assert "settings.enterprise.json" in results
    assert "settings.personal.json" in results
    assert json.loads((target_dir / "settings.json").read_text()) == {
        "model": "enterprise",
        "key": "test_key",
    }
    assert json.loads((target_dir / "settings.enterprise.json").read_text()) == {
        "model": "enterprise",
        "key": "test_key",
    }
    # personal 프로필은 별도 config 디렉토리(~/.claude-personal)의 settings.json으로 기록된다.
    assert json.loads((personal_dir / "settings.json").read_text()) == {
        "model": "personal",
        "key": "test_key",
    }
    # 평면 ~/.claude/settings.personal.json은 더 이상 생성하지 않는다.
    assert not (target_dir / "settings.personal.json").exists()
    # 공용 자산은 personal 디렉토리에 심링크로 재사용된다.
    claude_md_link = personal_dir / "CLAUDE.md"
    assert claude_md_link.is_symlink()
    assert claude_md_link.resolve() == (target_dir / "CLAUDE.md").resolve()


def test_sync_claude_global_config_includes_agents(tmp_path, mock_secrets_manager):
    """Claude 동기화 시 .claude/agents markdown 정의도 미러."""
    project_root = tmp_path / "ai-env"
    source_dir = project_root / ".claude"
    global_dir = source_dir / "global"
    global_dir.mkdir(parents=True)
    (global_dir / "CLAUDE.md").write_text("# Claude Global")

    agents_dir = source_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "router.md").write_text("# router")

    target_dir = tmp_path / "home" / ".claude"

    with (
        patch("ai_env.core.sync.get_project_root", return_value=project_root),
        patch("pathlib.Path.home", return_value=tmp_path / "home"),
    ):
        results = sync_claude_global_config()

    assert any("agents/" in key for key in results), f"missing agents in {results}"
    assert (target_dir / "agents" / "router.md").exists()


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


def test_collect_skill_sources_from_claude_skills(tmp_path):
    """.claude/skills 경로를 personal 소스로 사용."""
    project_root = tmp_path / "ai-env"
    skills_dir = project_root / ".claude" / "skills"

    (skills_dir / "my-private-skill").mkdir(parents=True)
    (skills_dir / "my-private-skill" / "SKILL.md").write_text("# personal skill")

    sources = _collect_skill_sources(project_root)
    names = [s.name for s in sources]

    assert len(sources) == 1
    assert "my-private-skill" in names


def test_collect_skill_sources_with_cde_skills(tmp_path):
    """--skills-include 사용 시 team(cde-skills symlink) 포함."""
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

    sources = _collect_skill_sources(project_root, skills_include=["cde-skills"])
    names = [s.name for s in sources]

    assert len(sources) == 3
    assert "git-worktree" in names
    assert "elasticsearch-query" in names
    assert "spark-debug" in names
    assert "scripts" not in names


def test_collect_skill_sources_with_cde_skills_subdir_layout(tmp_path):
    """skills/ 하위 team repo도 --skills-include로 포함."""
    project_root = tmp_path / "ai-env"
    skills_dir = project_root / ".claude" / "skills"

    # personal skill
    (skills_dir / "git-worktree").mkdir(parents=True)
    (skills_dir / "git-worktree" / "SKILL.md").write_text("# git worktree")

    # cde-skills 실제 디렉토리 (repo root/skills/<skill>/SKILL.md)
    cde_real = tmp_path / "cde-skills-repo"
    (cde_real / "skills" / "elasticsearch-query").mkdir(parents=True)
    (cde_real / "skills" / "elasticsearch-query" / "SKILL.md").write_text("# ES query")
    (cde_real / "skills" / "spark-debug").mkdir()
    (cde_real / "skills" / "spark-debug" / "SKILL.md").write_text("# Spark debug")
    # SKILL.md 없는 디렉토리는 무시
    (cde_real / "skills" / "_shared").mkdir()
    (cde_real / "skills" / "_shared" / "README.md").write_text("shared docs")

    # symlink 생성
    (project_root / "cde-skills").symlink_to(cde_real)

    sources = _collect_skill_sources(project_root, skills_include=["cde-skills"])
    names = [s.name for s in sources]

    assert len(sources) == 3
    assert "git-worktree" in names
    assert "elasticsearch-query" in names
    assert "spark-debug" in names
    assert "_shared" not in names


def test_collect_skill_sources_with_cde_skills_plugin_layout(tmp_path):
    """plugins/<name>/skills 레이아웃의 cde-skills 카테고리 스킬을 포함."""
    project_root = tmp_path / "ai-env"
    skills_dir = project_root / ".claude" / "skills"

    (skills_dir / "git-worktree").mkdir(parents=True)
    (skills_dir / "git-worktree" / "SKILL.md").write_text("# git worktree")

    cde_real = tmp_path / "cde-skills-repo"
    (cde_real / "skills" / "legacy-trino").mkdir(parents=True)
    (cde_real / "skills" / "legacy-trino" / "_SKILL.md").write_text("# legacy")
    plugin_skills = cde_real / "plugins" / "cde-skills" / "skills"
    (plugin_skills / "data" / "trino").mkdir(parents=True)
    (plugin_skills / "data" / "SKILL.md").write_text("# data")
    (plugin_skills / "data" / "trino" / "_SKILL.md").write_text("# trino")
    (plugin_skills / "orchestration").mkdir()
    (plugin_skills / "orchestration" / "SKILL.md").write_text("# orchestration")
    (plugin_skills / "_shared").mkdir()
    (plugin_skills / "_shared" / "README.md").write_text("shared")

    # repo root의 템플릿 SKILL.md는 실제 team skill 컨테이너가 아니므로 수집되면 안 된다.
    (cde_real / "templates").mkdir(parents=True)
    (cde_real / "templates" / "SKILL.md").write_text("# template")
    (project_root / "cde-skills").symlink_to(cde_real)

    sources = _collect_skill_sources(project_root)
    names = [s.name for s in sources]

    assert "git-worktree" in names
    assert "data" in names
    assert "orchestration" in names
    assert "templates" not in names
    assert "_shared" not in names


def test_sync_skills_merged(tmp_path):
    """--skills-include 사용 시 personal + team 스킬이 합쳐지는지 확인."""
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
    desc, count = _sync_skills_merged(
        project_root, dst, dry_run=False, skills_include=["cde-skills"]
    )

    assert count == 2
    assert (dst / "mcp-config" / "SKILL.md").exists()
    assert (dst / "trino-analyst" / "SKILL.md").exists()


def _git(cwd: Path, *args: str) -> None:
    """Run git for sync tests."""
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _configure_git_user(repo: Path) -> None:
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Tester")


def _write_skill(root: Path, name: str, body: str) -> None:
    skill_dir = root / ".claude" / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(body)


def test_collect_cde_ranking_skills_uses_develop_rebased_worktree(tmp_path):
    """cde-ranking 작업 브랜치는 develop 위에 rebase한 skill view를 동기화."""
    project_root = tmp_path / "ai-env"
    project_root.mkdir()
    repo = tmp_path / "cde-ranking-repo"
    repo.mkdir()

    _git(repo, "init", "-q")
    _configure_git_user(repo)

    _write_skill(repo, "base-skill", "# base")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "base")
    _git(repo, "branch", "-M", "develop")

    _git(repo, "checkout", "-q", "-b", "feature-ranking")
    _write_skill(repo, "feature-skill", "# feature")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "feature")

    _git(repo, "checkout", "-q", "develop")
    _write_skill(repo, "develop-skill", "# develop")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "develop update")
    _git(repo, "checkout", "-q", "feature-ranking")

    (project_root / "cde-ranking-skills").symlink_to(repo)

    sources = _collect_skill_sources(project_root)
    names = {source.name for source in sources}
    sync_worktree = project_root / ".claude" / "worktrees" / "cde-ranking-skills-rebased"

    assert {"base-skill", "develop-skill", "feature-skill"} <= names
    assert (
        subprocess.check_output(["git", "branch", "--show-current"], cwd=repo, text=True).strip()
        == "feature-ranking"
    )
    assert any(source.is_relative_to(sync_worktree) for source in sources)


def test_collect_cde_ranking_skills_fetches_origin_develop_for_rebase(tmp_path):
    """동기화 전 origin/develop을 fetch해 최신 develop 위의 skill view를 만든다."""
    project_root = tmp_path / "ai-env"
    project_root.mkdir()
    remote = tmp_path / "remote.git"
    upstream = tmp_path / "upstream"
    repo = tmp_path / "cde-ranking-repo"

    _git(tmp_path, "init", "--bare", "-q", str(remote))
    repo.mkdir()
    _git(repo, "init", "-q")
    _configure_git_user(repo)

    _write_skill(repo, "base-skill", "# base")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "base")
    _git(repo, "branch", "-M", "develop")
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-q", "-u", "origin", "develop")

    _git(repo, "checkout", "-q", "-b", "feature-ranking")
    _write_skill(repo, "feature-skill", "# feature")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "feature")

    _git(tmp_path, "clone", "-q", "--branch", "develop", str(remote), str(upstream))
    _configure_git_user(upstream)
    _write_skill(upstream, "remote-develop-skill", "# remote develop")
    _git(upstream, "add", ".")
    _git(upstream, "commit", "-q", "-m", "remote develop update")
    _git(upstream, "push", "-q", "origin", "develop")

    (project_root / "cde-ranking-skills").symlink_to(repo)

    sources = _collect_skill_sources(project_root)
    names = {source.name for source in sources}

    assert {"base-skill", "feature-skill", "remote-develop-skill"} <= names
    assert (
        subprocess.check_output(["git", "branch", "--show-current"], cwd=repo, text=True).strip()
        == "feature-ranking"
    )


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
    """--skills-include로 특정 팀 스킬 추가 + ALWAYS 팀 스킬은 항상 동행.

    팀 레포 layout(flat / subdir) 자체의 처리는
    test_collect_skill_sources_with_cde_skills(_subdir_layout)에서 별도로 검증한다.
    """
    project_root = _setup_multi_team_skills(tmp_path)

    sources = _collect_skill_sources(project_root, skills_include=["cde-skills"])
    names = [s.name for s in sources]

    assert "my-skill" in names  # personal은 항상 포함
    assert "es-query" in names  # cde-skills 포함
    # cde-ranking-skills 는 ALWAYS_TEAM_SKILLS 정책으로 항상 포함
    assert "ranking-lookup" in names
    assert "score-drilldown" in names


def test_collect_skills_exclude(tmp_path):
    """--skills-exclude=cde-ranking-skills 로 ALWAYS 정책을 옵트아웃."""
    project_root = _setup_multi_team_skills(tmp_path)

    sources = _collect_skill_sources(project_root, skills_exclude=["cde-ranking-skills"])
    names = [s.name for s in sources]

    assert "my-skill" in names  # personal은 항상 포함
    assert "es-query" in names  # cde-skills 포함 (filter 모드)
    assert "ranking-lookup" not in names  # 명시적 제외로 ALWAYS 옵트아웃
    assert "score-drilldown" not in names


def test_collect_skills_no_filter(tmp_path):
    """필터 없어도 personal + own + ALWAYS 팀 스킬은 포함."""
    project_root = _setup_multi_team_skills(tmp_path)

    sources = _collect_skill_sources(project_root)
    names = [s.name for s in sources]

    assert "my-skill" in names  # personal
    assert "es-query" in names  # cde-skills (ALWAYS)
    assert "ranking-lookup" in names  # cde-ranking-skills (ALWAYS)
    assert "score-drilldown" in names


def test_collect_skills_always_no_double_include(tmp_path):
    """--skills-all 같이 ALWAYS 팀 스킬이 include 에 들어와도 dedup 보장."""
    project_root = _setup_multi_team_skills(tmp_path)

    sources = _collect_skill_sources(
        project_root, skills_include=["cde-skills", "cde-ranking-skills"]
    )
    names = [s.name for s in sources]

    # 중복 없이 한 번씩만
    assert names.count("ranking-lookup") == 1
    assert names.count("score-drilldown") == 1
    assert names.count("es-query") == 1


def test_safe_copy_skill_tree_prunes_large_generated_artifacts(tmp_path):
    """스킬 복사 시 큰 생성 산출물은 제외하고 문서/스크립트는 보존."""
    source = tmp_path / "source-skill"
    target = tmp_path / "target-skill"
    (source / "scripts").mkdir(parents=True)
    (source / "docs").mkdir()
    (source / "SKILL.md").write_text("# skill")
    (source / "scripts" / "helper.py").write_text("print('ok')\n")
    (source / "docs" / "small.html").write_text("<p>small</p>")
    large_artifact = source / "ontology.db"
    with large_artifact.open("wb") as f:
        f.truncate(6 * 1024 * 1024)
    (source / ".pytest_cache").mkdir()
    (source / ".pytest_cache" / "README").write_text("cache")

    safe_copy_skill_tree(source, target)

    assert (target / "SKILL.md").exists()
    assert (target / "scripts" / "helper.py").exists()
    assert (target / "docs" / "small.html").exists()
    assert not (target / "ontology.db").exists()
    assert not (target / ".pytest_cache").exists()


def test_sync_codex_global_config(tmp_path, mock_secrets_manager):
    """Codex 동기화 시 AGENTS.md와 skills/가 생성되는지 확인."""
    project_root = tmp_path / "ai-env"
    global_dir = project_root / ".claude" / "global"
    global_dir.mkdir(parents=True)
    (global_dir / "CLAUDE.md").write_text("# Global Instructions")
    skills_dir = project_root / ".claude" / "skills"
    (skills_dir / "spec-manager").mkdir(parents=True)
    (skills_dir / "spec-manager" / "SKILL.md").write_text("# spec")

    target_dir = tmp_path / "home" / ".codex"

    with (
        patch("ai_env.core.sync.get_project_root", return_value=project_root),
        patch("pathlib.Path.home", return_value=tmp_path / "home"),
    ):
        results = sync_codex_global_config()

    assert "AGENTS.md" in results
    assert any("skills/" in key for key in results)
    agents_md = target_dir / "AGENTS.md"
    assert agents_md.exists()
    assert "# Global Instructions" in agents_md.read_text()
    assert (target_dir / "skills" / "spec-manager" / "SKILL.md").exists()


def test_sync_codex_global_config_dry_run(tmp_path, mock_secrets_manager):
    """Codex dry_run 시 파일 미생성 확인."""
    project_root = tmp_path / "ai-env"
    global_dir = project_root / ".claude" / "global"
    global_dir.mkdir(parents=True)
    (global_dir / "CLAUDE.md").write_text("# Global Instructions")
    skills_dir = project_root / ".claude" / "skills"
    (skills_dir / "spec-manager").mkdir(parents=True)
    (skills_dir / "spec-manager" / "SKILL.md").write_text("# spec")

    target_dir = tmp_path / "home" / ".codex"

    with (
        patch("ai_env.core.sync.get_project_root", return_value=project_root),
        patch("pathlib.Path.home", return_value=tmp_path / "home"),
    ):
        results = sync_codex_global_config(dry_run=True)

    assert "AGENTS.md" in results
    assert not (target_dir / "AGENTS.md").exists()
    assert not (target_dir / "skills").exists()


def test_sync_codex_global_config_mirrors_personal_home(tmp_path, mock_secrets_manager):
    """Codex 동기화 시 ~/.codex-personal에 공용 자산 심링크를 만든다.

    `codex personal`(CODEX_HOME=~/.codex-personal)은 별도 auth.json만 분리하고
    AGENTS.md/skills/commands/agents 등 자산은 ~/.codex를 심링크로 재사용한다.
    """
    project_root = tmp_path / "ai-env"
    global_dir = project_root / ".claude" / "global"
    global_dir.mkdir(parents=True)
    (global_dir / "CLAUDE.md").write_text("# Global Instructions")
    skills_dir = project_root / ".claude" / "skills"
    (skills_dir / "spec-manager").mkdir(parents=True)
    (skills_dir / "spec-manager" / "SKILL.md").write_text("# spec")

    home_dir = tmp_path / "home"
    codex_dir = home_dir / ".codex"
    personal_dir = home_dir / ".codex-personal"

    with (
        patch("ai_env.core.sync.get_project_root", return_value=project_root),
        patch("pathlib.Path.home", return_value=home_dir),
    ):
        results = sync_codex_global_config()

    # AGENTS.md는 personal 디렉토리에 심링크로 재사용된다.
    agents_link = personal_dir / "AGENTS.md"
    assert agents_link.is_symlink()
    assert agents_link.resolve() == (codex_dir / "AGENTS.md").resolve()
    # skills도 심링크
    skills_link = personal_dir / "skills"
    assert skills_link.is_symlink()
    assert skills_link.resolve() == (codex_dir / "skills").resolve()
    # auth.json은 절대 심링크하지 않는다(계정 분리 보장).
    assert not (personal_dir / "auth.json").exists()
    assert any("codex-personal" in key for key in results)


def test_sync_codex_global_config_config_toml_symlink_survives_first_sync(
    tmp_path, mock_secrets_manager
):
    """config.toml은 generator가 나중에 생성하므로, 첫 sync에서도 dangling 심링크로 만들어 둔다.

    이렇게 하면 같은 sync 실행에서 generator가 ~/.codex/config.toml을 쓰는 순간
    ~/.codex-personal/config.toml 심링크가 자동으로 해석된다(첫 sync 갭 제거).
    """
    project_root = tmp_path / "ai-env"
    global_dir = project_root / ".claude" / "global"
    global_dir.mkdir(parents=True)
    (global_dir / "CLAUDE.md").write_text("# Global Instructions")

    home_dir = tmp_path / "home"
    codex_dir = home_dir / ".codex"
    personal_dir = home_dir / ".codex-personal"

    # 첫 sync: ~/.codex/config.toml이 아직 없는 상태 (generator 미실행)
    with (
        patch("ai_env.core.sync.get_project_root", return_value=project_root),
        patch("pathlib.Path.home", return_value=home_dir),
    ):
        sync_codex_global_config()

    config_link = personal_dir / "config.toml"
    # 타깃이 아직 없어도 심링크 자체는 만들어져야 한다(dangling 허용).
    assert config_link.is_symlink()
    assert config_link.readlink() == (codex_dir / "config.toml")
    # 아직 타깃이 없으므로 해석되지 않는다.
    assert not config_link.exists()

    # generator가 config.toml을 쓰면 동일 심링크가 즉시 해석된다.
    (codex_dir / "config.toml").write_text('model = "gpt-5.5"\n')
    assert config_link.exists()
    assert config_link.read_text() == 'model = "gpt-5.5"\n'

    # 두 번째 sync도 idempotent (심링크 churn 없음)
    with (
        patch("ai_env.core.sync.get_project_root", return_value=project_root),
        patch("pathlib.Path.home", return_value=home_dir),
    ):
        sync_codex_global_config()
    assert config_link.is_symlink()
    assert config_link.read_text() == 'model = "gpt-5.5"\n'


def test_sync_codex_global_config_writes_codex_hooks_json(tmp_path, mock_secrets_manager):
    """Codex 동기화 시 hooks.json과 hook scripts를 생성한다."""
    project_root = tmp_path / "ai-env"
    global_dir = project_root / ".claude" / "global"
    global_dir.mkdir(parents=True)
    (global_dir / "CLAUDE.md").write_text("# Global Instructions")

    hooks_dir = project_root / ".claude" / "hooks"
    hooks_dir.mkdir(parents=True)
    for name in ("session_start.sh", "session_end.sh", "pre_compact.sh", "security_guard.sh"):
        (hooks_dir / name).write_text("#!/usr/bin/env bash\necho hook\n")

    codex_hooks_dir = project_root / ".codex" / "hooks"
    codex_hooks_dir.mkdir(parents=True)
    (codex_hooks_dir / "hook_event_log.sh").write_text("#!/usr/bin/env bash\necho log\n")

    target_dir = tmp_path / "home" / ".codex"

    with (
        patch("ai_env.core.sync.get_project_root", return_value=project_root),
        patch("pathlib.Path.home", return_value=tmp_path / "home"),
    ):
        results = sync_codex_global_config()

    assert "hooks.json" in results
    hooks_json = target_dir / "hooks.json"
    content = hooks_json.read_text()
    assert '"async"' not in content
    assert str(target_dir / "hooks" / "session_end.sh") in content
    assert str(target_dir / "hooks" / "hook_event_log.sh") in content
    assert (target_dir / "hooks" / "session_end.sh").exists()
    assert (target_dir / "hooks" / "hook_event_log.sh").exists()


def test_sync_codex_global_config_overwrites_invalid_hooks_json(tmp_path, mock_secrets_manager):
    """깨진 hooks.json이 있어도 Codex 동기화가 유효한 파일로 덮어쓴다."""
    project_root = tmp_path / "ai-env"
    global_dir = project_root / ".claude" / "global"
    global_dir.mkdir(parents=True)
    (global_dir / "CLAUDE.md").write_text("# Global Instructions")

    target_dir = tmp_path / "home" / ".codex"
    target_dir.mkdir(parents=True)
    hooks_json = target_dir / "hooks.json"
    hooks_json.write_text("{not-json")

    with (
        patch("ai_env.core.sync.get_project_root", return_value=project_root),
        patch("pathlib.Path.home", return_value=tmp_path / "home"),
    ):
        results = sync_codex_global_config()

    assert "AGENTS.md" in results
    assert "hooks.json" in results
    assert json.loads(hooks_json.read_text())["hooks"]["SessionEnd"]


def test_sync_codex_no_source(tmp_path, mock_secrets_manager):
    """소스 CLAUDE.md 없으면 빈 결과 반환."""
    project_root = tmp_path / "ai-env"
    project_root.mkdir(parents=True)

    with (
        patch("ai_env.core.sync.get_project_root", return_value=project_root),
        patch("pathlib.Path.home", return_value=tmp_path / "home"),
    ):
        results = sync_codex_global_config()

    assert results == {}


def test_sync_codex_includes_commands_and_profile(tmp_path, mock_secrets_manager):
    """Codex sync 시 commands/, agents/, project-profile.yaml도 미러."""
    project_root = tmp_path / "ai-env"
    global_dir = project_root / ".claude" / "global"
    global_dir.mkdir(parents=True)
    (global_dir / "CLAUDE.md").write_text("# Global")

    # commands/ 트리: 루트 .md + phases/ 하위 .md
    commands_dir = project_root / ".claude" / "commands"
    commands_dir.mkdir(parents=True)
    (commands_dir / "workflow.md").write_text("# workflow")
    (commands_dir / "phases").mkdir()
    (commands_dir / "phases" / "wf-init.md").write_text("# wf-init")

    # agents/ 트리
    agents_dir = project_root / ".claude" / "agents"
    agents_dir.mkdir()
    (agents_dir / "router.md").write_text("# router")

    # project-profile.yaml
    (project_root / ".claude" / "project-profile.yaml").write_text("project:\n  name: t\n")

    target_root = tmp_path / "home" / ".codex"

    with (
        patch("ai_env.core.sync.get_project_root", return_value=project_root),
        patch("pathlib.Path.home", return_value=tmp_path / "home"),
    ):
        results = sync_codex_global_config()

    # 결과에 commands/와 project-profile.yaml이 포함되어야 함
    assert any("commands/" in key for key in results), f"missing commands in {results}"
    assert any("agents/" in key for key in results), f"missing agents in {results}"
    assert "project-profile.yaml" in results

    # 실제 파일 검증
    assert (target_root / "commands" / "workflow.md").exists()
    assert (target_root / "commands" / "phases" / "wf-init.md").exists()
    assert (target_root / "agents" / "router.md").exists()
    assert (target_root / "project-profile.yaml").exists()


def test_sync_codex_commands_overwrite_clean(tmp_path, mock_secrets_manager):
    """Codex sync 두 번 호출해도 commands/ 트리가 깔끔하게 갱신됨."""
    project_root = tmp_path / "ai-env"
    global_dir = project_root / ".claude" / "global"
    global_dir.mkdir(parents=True)
    (global_dir / "CLAUDE.md").write_text("# G")

    commands_dir = project_root / ".claude" / "commands"
    commands_dir.mkdir(parents=True)
    (commands_dir / "first.md").write_text("# 1")

    target_root = tmp_path / "home" / ".codex"

    with (
        patch("ai_env.core.sync.get_project_root", return_value=project_root),
        patch("pathlib.Path.home", return_value=tmp_path / "home"),
    ):
        sync_codex_global_config()

    # 1차 sync 결과: first.md만 존재
    assert (target_root / "commands" / "first.md").exists()

    # 소스에서 first.md 제거하고 second.md 추가
    (commands_dir / "first.md").unlink()
    (commands_dir / "second.md").write_text("# 2")

    with (
        patch("ai_env.core.sync.get_project_root", return_value=project_root),
        patch("pathlib.Path.home", return_value=tmp_path / "home"),
    ):
        sync_codex_global_config()

    # 2차 sync 결과: first.md는 사라지고 second.md가 있어야 함
    assert not (target_root / "commands" / "first.md").exists()
    assert (target_root / "commands" / "second.md").exists()


def test_sync_hooks_directory(tmp_path):
    """hooks/ 디렉토리 동기화 및 .sh 실행 권한 확인."""
    src = tmp_path / "hooks"
    src.mkdir()
    (src / "session_start.sh").write_text("#!/usr/bin/env bash\necho start")
    (src / "session_end.sh").write_text("#!/usr/bin/env bash\necho end")
    (src / "pre_compact.sh").write_text("#!/usr/bin/env bash\necho compact")

    dst = tmp_path / "target" / "hooks"

    desc, count = _sync_file_or_dir(src, dst)

    assert count == 3
    assert "hooks/" in desc
    assert "3 scripts" in desc
    assert (dst / "session_start.sh").exists()
    assert (dst / "session_end.sh").exists()
    assert (dst / "pre_compact.sh").exists()

    # 실행 권한 확인
    for sh_file in dst.glob("*.sh"):
        mode = sh_file.stat().st_mode
        assert mode & stat.S_IXUSR, f"{sh_file.name} should be executable"


def test_sync_hooks_directory_dry_run(tmp_path):
    """hooks/ dry_run 시 파일 미복사."""
    src = tmp_path / "hooks"
    src.mkdir()
    (src / "session_start.sh").write_text("#!/usr/bin/env bash\necho start")

    dst = tmp_path / "target" / "hooks"

    desc, count = _sync_file_or_dir(src, dst, dry_run=True)

    assert count == 1
    assert not dst.exists()


def test_sync_hooks_overwrites_existing(tmp_path):
    """기존 hooks/ 디렉토리가 있으면 덮어쓰기."""
    src = tmp_path / "hooks"
    src.mkdir()
    (src / "session_start.sh").write_text("#!/usr/bin/env bash\necho new")

    dst = tmp_path / "target" / "hooks"
    dst.mkdir(parents=True)
    (dst / "old_hook.sh").write_text("#!/usr/bin/env bash\necho old")

    _sync_file_or_dir(src, dst)

    assert (dst / "session_start.sh").exists()
    assert not (dst / "old_hook.sh").exists()  # 기존 파일 제거됨


def test_extract_skill_summary_inline(tmp_path):
    """인라인 description이 있는 SKILL.md에서 name+desc 추출."""
    skill_dir = tmp_path / "my-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: my-skill\ndescription: 스킬 설명입니다\n---\n# Content"
    )

    result = _extract_skill_summary(skill_dir)
    assert result == ("my-skill", "스킬 설명입니다")


def test_extract_skill_summary_multiline(tmp_path):
    """멀티라인(|) description에서 첫 줄만 추출."""
    skill_dir = tmp_path / "multi-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: multi-skill\ndescription: |\n  첫 번째 줄 설명\n  두 번째 줄\n---\n"
    )

    result = _extract_skill_summary(skill_dir)
    assert result is not None
    assert result[0] == "multi-skill"
    assert result[1] == "첫 번째 줄 설명"


def test_extract_skill_summary_no_frontmatter(tmp_path):
    """frontmatter 없는 SKILL.md는 None 반환."""
    skill_dir = tmp_path / "no-fm"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Just a heading\nSome content")

    result = _extract_skill_summary(skill_dir)
    assert result is None


def test_extract_skill_summary_no_skill_md(tmp_path):
    """SKILL.md 없으면 None 반환."""
    skill_dir = tmp_path / "empty"
    skill_dir.mkdir()

    result = _extract_skill_summary(skill_dir)
    assert result is None


def test_build_skills_index(tmp_path):
    """스킬 인덱스 Markdown 생성 확인."""
    project_root = tmp_path / "ai-env"
    skills_dir = project_root / ".claude" / "skills"

    (skills_dir / "spec-manager").mkdir(parents=True)
    (skills_dir / "spec-manager" / "SKILL.md").write_text(
        "---\nname: spec-manager\ndescription: Spec 문서 관리\n---\n"
    )
    (skills_dir / "code-review").mkdir()
    (skills_dir / "code-review" / "SKILL.md").write_text(
        "---\nname: code-review\ndescription: 코드 리뷰 통합\n---\n"
    )

    index = _build_skills_index(project_root)

    assert "## Available Skills" in index
    assert "**spec-manager**" in index
    assert "**code-review**" in index
    assert "Spec 문서 관리" in index
    assert "코드 리뷰 통합" in index


def test_build_skills_index_empty(tmp_path):
    """스킬 없으면 빈 문자열 반환."""
    project_root = tmp_path / "ai-env"
    project_root.mkdir(parents=True)

    index = _build_skills_index(project_root)
    assert index == ""


def test_sync_codex_includes_skills_index(tmp_path, mock_secrets_manager):
    """Codex 동기화 시 AGENTS.md에 스킬 인덱스가 포함되는지 확인."""
    project_root = tmp_path / "ai-env"
    global_dir = project_root / ".claude" / "global"
    global_dir.mkdir(parents=True)
    (global_dir / "CLAUDE.md").write_text("# Global Instructions")

    # 스킬 생성
    skills_dir = project_root / ".claude" / "skills"
    (skills_dir / "task-impl").mkdir(parents=True)
    (skills_dir / "task-impl" / "SKILL.md").write_text(
        "---\nname: task-implement\ndescription: TDD 코드 구현\n---\n"
    )

    target_dir = tmp_path / "home" / ".codex"

    with (
        patch("ai_env.core.sync.get_project_root", return_value=project_root),
        patch("pathlib.Path.home", return_value=tmp_path / "home"),
    ):
        results = sync_codex_global_config()

    assert "AGENTS.md" in results
    agents_md = target_dir / "AGENTS.md"
    content = agents_md.read_text()
    assert "# Global Instructions" in content
    assert "## Available Skills" in content
    assert "**task-implement**" in content
    assert "TDD 코드 구현" in content


def test_sync_codex_global_config_prunes_stale_skills_but_keeps_meta(
    tmp_path, mock_secrets_manager
):
    """Codex 동기화는 소스에 없는 stale 스킬을 제거하되, 시스템 메타 디렉토리는 보존.

    Codex 0.125+ 가 SKILL.md frontmatter를 엄격히 파싱하므로 stale 파일은
    경고를 유발한다. 따라서 ai-env가 관리하지 않는 외부 스킬(예: 'playwright')은
    제거하고, dotfile/`_`-prefix 디렉토리(`.system`)만 보존한다.
    """
    project_root = tmp_path / "ai-env"
    global_dir = project_root / ".claude" / "global"
    global_dir.mkdir(parents=True)
    (global_dir / "CLAUDE.md").write_text("# Global Instructions")

    skills_dir = project_root / ".claude" / "skills"
    (skills_dir / "research").mkdir(parents=True)
    (skills_dir / "research" / "SKILL.md").write_text("# research")

    target_dir = tmp_path / "home" / ".codex" / "skills"
    (target_dir / ".system").mkdir(parents=True)
    (target_dir / ".system" / ".codex-system-skills.marker").write_text("marker")
    (target_dir / "playwright").mkdir()
    (target_dir / "playwright" / "SKILL.md").write_text("# stale external")

    with (
        patch("ai_env.core.sync.get_project_root", return_value=project_root),
        patch("pathlib.Path.home", return_value=tmp_path / "home"),
    ):
        sync_codex_global_config()

    # 메타(.system)는 보존
    assert (target_dir / ".system" / ".codex-system-skills.marker").exists()
    # 소스에 없는 stale 스킬은 제거
    assert not (target_dir / "playwright").exists()
    # 소스의 신규 스킬은 정규화되어 추가
    assert (target_dir / "research" / "SKILL.md").exists()


def test_sync_codex_global_config_normalizes_skill_frontmatter(tmp_path, mock_secrets_manager):
    """Codex skills 동기화 시 느슨한 frontmatter를 유효 YAML로 변환한다."""
    project_root = tmp_path / "ai-env"
    global_dir = project_root / ".claude" / "global"
    global_dir.mkdir(parents=True)
    (global_dir / "CLAUDE.md").write_text("# Global Instructions")

    skills_dir = project_root / ".claude" / "skills"
    (skills_dir / "spark-debug").mkdir(parents=True)
    (skills_dir / "spark-debug" / "SKILL.md").write_text(
        """---
name: spark-debug
description: Spark application 디버깅 및 로그 모니터링 도구입니다.
  - Kerberos 인증 (kinit) 자동화
  - YARN application 상태 조회
---

# Spark Debug
"""
    )

    target_dir = tmp_path / "home" / ".codex"

    with (
        patch("ai_env.core.sync.get_project_root", return_value=project_root),
        patch("pathlib.Path.home", return_value=tmp_path / "home"),
    ):
        sync_codex_global_config()

    content = (target_dir / "skills" / "spark-debug" / "SKILL.md").read_text()
    assert content.startswith("---\nname: spark-debug\n")
    assert "description:" in content
    assert "Kerberos 인증" in content


def test_sync_claude_global_config_includes_hooks(tmp_path, mock_secrets_manager):
    """sync_claude_global_config에서 hooks/ 동기화 확인."""
    project_root = tmp_path / "ai-env"
    source_dir = project_root / ".claude"
    global_dir = source_dir / "global"
    global_dir.mkdir(parents=True)

    (global_dir / "CLAUDE.md").write_text("# Claude Global")
    (global_dir / "settings.json.template").write_text('{"key": "${API_KEY}"}')

    hooks_dir = source_dir / "hooks"
    hooks_dir.mkdir()
    (hooks_dir / "session_start.sh").write_text("#!/usr/bin/env bash\necho start")

    target_dir = tmp_path / "home" / ".claude"

    with (
        patch("ai_env.core.sync.get_project_root", return_value=project_root),
        patch("pathlib.Path.home", return_value=tmp_path / "home"),
    ):
        results = sync_claude_global_config()

    assert any("hooks/" in k for k in results)
    hooks_dst = target_dir / "hooks" / "session_start.sh"
    assert hooks_dst.exists()
    assert hooks_dst.stat().st_mode & stat.S_IXUSR


def test_sync_cmux_hooks_included_by_default(tmp_path, mock_secrets_manager):
    """cmux_enabled=true(기본값)일 때 cmux_notify.sh가 동기화되고 settings.json에 cmux 훅 포함."""
    project_root = tmp_path / "ai-env"
    source_dir = project_root / ".claude"
    global_dir = source_dir / "global"
    global_dir.mkdir(parents=True)

    (global_dir / "CLAUDE.md").write_text("# Claude Global")
    settings_content = """{
  "hooks": {
    "SessionStart": [{"matcher": "", "hooks": [
      {"type": "command", "command": "bash ~/.claude/hooks/session_start.sh"},
      {"type": "command", "command": "bash ~/.claude/hooks/cmux_notify.sh", "async": true}
    ]}],
    "Stop": [{"matcher": "", "hooks": [
      {"type": "command", "command": "bash ~/.claude/hooks/cmux_notify.sh", "async": true}
    ]}]
  }
}"""
    (global_dir / "settings.json.template").write_text(settings_content)

    hooks_dir = source_dir / "hooks"
    hooks_dir.mkdir()
    (hooks_dir / "session_start.sh").write_text("#!/usr/bin/env bash\necho start")
    (hooks_dir / "cmux_notify.sh").write_text("#!/usr/bin/env bash\necho cmux")

    config_dir = project_root / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "settings.yaml").write_text("cmux_enabled: true\n")

    target_dir = tmp_path / "home" / ".claude"

    with (
        patch("ai_env.core.sync.get_project_root", return_value=project_root),
        patch("ai_env.core.config.get_project_root", return_value=project_root),
        patch("pathlib.Path.home", return_value=tmp_path / "home"),
    ):
        sync_claude_global_config()

    # cmux_notify.sh가 hooks에 복사됨
    assert (target_dir / "hooks" / "cmux_notify.sh").exists()
    # settings.json에 cmux 훅이 포함됨
    import json

    settings = json.loads((target_dir / "settings.json").read_text())
    assert "Stop" in settings["hooks"]


def test_sync_cmux_hooks_excluded_when_disabled(tmp_path, mock_secrets_manager):
    """cmux_enabled=false일 때 cmux_notify.sh 제외, settings.json에서 cmux 훅 제거."""
    project_root = tmp_path / "ai-env"
    source_dir = project_root / ".claude"
    global_dir = source_dir / "global"
    global_dir.mkdir(parents=True)

    (global_dir / "CLAUDE.md").write_text("# Claude Global")
    settings_content = """{
  "hooks": {
    "SessionStart": [{"matcher": "", "hooks": [
      {"type": "command", "command": "bash ~/.claude/hooks/session_start.sh"},
      {"type": "command", "command": "bash ~/.claude/hooks/cmux_notify.sh", "async": true}
    ]}],
    "Stop": [{"matcher": "", "hooks": [
      {"type": "command", "command": "bash ~/.claude/hooks/cmux_notify.sh", "async": true}
    ]}]
  }
}"""
    (global_dir / "settings.json.template").write_text(settings_content)

    hooks_dir = source_dir / "hooks"
    hooks_dir.mkdir()
    (hooks_dir / "session_start.sh").write_text("#!/usr/bin/env bash\necho start")
    (hooks_dir / "cmux_notify.sh").write_text("#!/usr/bin/env bash\necho cmux")

    config_dir = project_root / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "settings.yaml").write_text("cmux_enabled: false\n")

    target_dir = tmp_path / "home" / ".claude"

    with (
        patch("ai_env.core.sync.get_project_root", return_value=project_root),
        patch("ai_env.core.config.get_project_root", return_value=project_root),
        patch("pathlib.Path.home", return_value=tmp_path / "home"),
    ):
        sync_claude_global_config()

    # cmux_notify.sh가 hooks에 없어야 함
    assert not (target_dir / "hooks" / "cmux_notify.sh").exists()
    # session_start.sh는 있어야 함
    assert (target_dir / "hooks" / "session_start.sh").exists()
    # settings.json에서 Stop 카테고리 제거 (cmux 전용이었으므로)
    import json

    settings = json.loads((target_dir / "settings.json").read_text())
    assert "Stop" not in settings["hooks"]
    # SessionStart는 남아있되, cmux 훅만 제거
    session_hooks = settings["hooks"]["SessionStart"][0]["hooks"]
    assert len(session_hooks) == 1
    assert "session_start.sh" in session_hooks[0]["command"]
