"""Tests for project-local Claude to Codex sync."""

from __future__ import annotations

from pathlib import Path

from ai_env.core.project_sync import sync_project_claude_to_codex


def test_sync_project_claude_to_codex_links_files(tmp_path: Path) -> None:
    """기본 모드는 AGENTS.md를 링크하고 skills는 Codex용으로 복사한다."""
    project_dir = tmp_path / "sample-project"
    (project_dir / ".claude" / "skills" / "research").mkdir(parents=True)
    (project_dir / ".claude" / "skills" / "research" / "SKILL.md").write_text("# research")
    (project_dir / "CLAUDE.md").write_text("# Project Claude")

    results = sync_project_claude_to_codex(project_dir)

    assert len(results) == 2
    assert (project_dir / "AGENTS.md").is_symlink()
    assert (project_dir / "AGENTS.md").resolve() == (project_dir / "CLAUDE.md").resolve()
    assert not (project_dir / ".codex" / "skills").is_symlink()
    assert (project_dir / ".codex" / "skills" / "research" / "SKILL.md").exists()


def test_sync_project_claude_to_codex_copy_mode(tmp_path: Path) -> None:
    """copy 모드는 복사본을 만든다."""
    project_dir = tmp_path / "sample-project"
    (project_dir / ".claude" / "skills" / "research").mkdir(parents=True)
    (project_dir / ".claude" / "skills" / "research" / "SKILL.md").write_text("# research")
    (project_dir / "CLAUDE.md").write_text("# Project Claude")

    results = sync_project_claude_to_codex(project_dir, use_copy=True)

    assert len(results) == 2
    assert not (project_dir / "AGENTS.md").is_symlink()
    assert not (project_dir / ".codex" / "skills").is_symlink()
    assert (project_dir / "AGENTS.md").read_text() == "# Project Claude"
    skill_text = (project_dir / ".codex" / "skills" / "research" / "SKILL.md").read_text()
    assert skill_text.startswith("---\nname: research\n")
    assert "# research" in skill_text


def test_sync_project_claude_to_codex_backs_up_existing_targets(tmp_path: Path) -> None:
    """기존 일반 파일/디렉토리는 백업 후 교체한다."""
    project_dir = tmp_path / "sample-project"
    (project_dir / ".claude" / "skills" / "research").mkdir(parents=True)
    (project_dir / ".claude" / "skills" / "research" / "SKILL.md").write_text("# research")
    (project_dir / "CLAUDE.md").write_text("# Project Claude")

    (project_dir / "AGENTS.md").write_text("old agents")
    (project_dir / ".codex" / "skills").mkdir(parents=True)
    (project_dir / ".codex" / "skills" / "old.txt").write_text("old skill")

    results = sync_project_claude_to_codex(project_dir)

    agents_result = next(result for result in results if result.name == "AGENTS.md")
    skills_result = next(result for result in results if result.name == ".codex/skills")

    assert agents_result.backup_path is not None
    assert skills_result.backup_path is not None
    assert agents_result.backup_path.exists()
    assert skills_result.backup_path.exists()
    assert agents_result.backup_path.read_text() == "old agents"
    assert (skills_result.backup_path / "old.txt").read_text() == "old skill"
    assert (project_dir / "AGENTS.md").is_symlink()
    assert not (project_dir / ".codex" / "skills").is_symlink()


def test_sync_project_claude_to_codex_missing_sources(tmp_path: Path) -> None:
    """소스가 없으면 missing 상태를 반환한다."""
    project_dir = tmp_path / "sample-project"
    project_dir.mkdir()

    results = sync_project_claude_to_codex(project_dir)

    assert [result.status for result in results] == ["missing", "missing"]


def test_sync_project_claude_to_codex_dry_run(tmp_path: Path) -> None:
    """dry-run은 파일을 만들지 않는다."""
    project_dir = tmp_path / "sample-project"
    (project_dir / ".claude" / "skills" / "research").mkdir(parents=True)
    (project_dir / ".claude" / "skills" / "research" / "SKILL.md").write_text("# research")
    (project_dir / "CLAUDE.md").write_text("# Project Claude")

    results = sync_project_claude_to_codex(project_dir, dry_run=True)

    assert [result.status for result in results] == ["linked", "copied"]
    assert not (project_dir / "AGENTS.md").exists()
    assert not (project_dir / ".codex" / "skills").exists()
