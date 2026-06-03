"""ai_env.core.session_save 단위 테스트."""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path

import pytest
from ai_env.core.session_save import (
    DEFAULT_SUBDIR,
    GitSnapshot,
    _next_available_path,
    build_session_note,
    collect_git_snapshot,
    save_session,
    slugify,
)


@pytest.fixture()
def fresh_repo(tmp_path: Path) -> Path:
    """깨끗한 git 저장소 픽스처."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo, check=True)
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)
    return repo


class TestSlugify:
    def test_basic_replaces_spaces_with_dashes(self) -> None:
        assert slugify("hello world") == "hello-world"

    def test_drops_special_characters(self) -> None:
        assert slugify("a/b:c.d") == "abcd"

    def test_preserves_korean(self) -> None:
        assert slugify("세션 저장 메모") == "세션-저장-메모"

    def test_collapses_multiple_dashes(self) -> None:
        assert slugify("a---b") == "a-b"

    def test_empty_falls_back(self) -> None:
        assert slugify("") == "session"
        assert slugify("///") == "session"

    def test_truncates_long_text(self) -> None:
        result = slugify("a" * 200, max_len=20)
        assert len(result) == 20


class TestNextAvailablePath:
    def test_returns_base_when_free(self, tmp_path: Path) -> None:
        result = _next_available_path(tmp_path, "note")
        assert result == tmp_path / "note.md"

    def test_appends_suffix_on_collision(self, tmp_path: Path) -> None:
        (tmp_path / "note.md").write_text("x")
        result = _next_available_path(tmp_path, "note")
        assert result == tmp_path / "note-2.md"

    def test_increments_until_free(self, tmp_path: Path) -> None:
        (tmp_path / "note.md").write_text("x")
        (tmp_path / "note-2.md").write_text("x")
        result = _next_available_path(tmp_path, "note")
        assert result == tmp_path / "note-3.md"


class TestCollectGitSnapshot:
    def test_outside_repo(self, tmp_path: Path) -> None:
        snap = collect_git_snapshot(tmp_path)
        assert snap.is_repo is False
        assert snap.branch == ""

    def test_clean_repo(self, fresh_repo: Path) -> None:
        snap = collect_git_snapshot(fresh_repo)
        assert snap.is_repo is True
        assert snap.branch  # 'main' or 'master' depending on git config
        assert "init" in snap.log
        assert snap.status == ""  # clean

    def test_dirty_repo(self, fresh_repo: Path) -> None:
        (fresh_repo / "README.md").write_text("changed\n", encoding="utf-8")
        snap = collect_git_snapshot(fresh_repo)
        assert "README.md" in snap.status
        assert "README.md" in snap.diff_stat


class TestBuildSessionNote:
    def test_includes_frontmatter_and_title(self) -> None:
        snap = GitSnapshot(branch="main", is_repo=True)
        body = build_session_note(
            title="hello",
            note="my note",
            snapshot=snap,
            project_name="ai-env",
            now=datetime(2026, 4, 30, 18, 30),
        )
        assert body.startswith("---\n")
        assert "title: hello" in body
        assert "tags: [session, ai-env]" in body
        assert "project: ai-env" in body
        assert "branch: main" in body
        assert "# hello" in body
        assert "## Note" in body
        assert "my note" in body
        assert "## Ontology Seeds" in body

    def test_omits_note_section_when_no_note(self) -> None:
        snap = GitSnapshot(branch="main", is_repo=True)
        body = build_session_note(
            title="t",
            note=None,
            snapshot=snap,
            now=datetime(2026, 4, 30, 18, 30),
        )
        assert "## Note" not in body

    def test_omits_git_section_when_not_repo(self) -> None:
        snap = GitSnapshot()  # is_repo False
        body = build_session_note(
            title="t",
            note="n",
            snapshot=snap,
            now=datetime(2026, 4, 30, 18, 30),
        )
        assert "## Git Snapshot" not in body
        assert "## Recent Changes" not in body

    def test_includes_extras(self) -> None:
        snap = GitSnapshot()
        body = build_session_note(
            title="t",
            note=None,
            snapshot=snap,
            extras={"Decisions": "use uv", "TODO": "write tests"},
            now=datetime(2026, 4, 30, 18, 30),
        )
        assert "## Extras" in body
        assert "### Decisions" in body
        assert "use uv" in body
        assert "### TODO" in body


class TestSaveSession:
    def test_dry_run_returns_body_without_writing(self, tmp_path: Path, fresh_repo: Path) -> None:
        result = save_session(
            note="dry run note",
            vault=tmp_path / "vault",
            cwd=fresh_repo,
            dry_run=True,
            now=datetime(2026, 4, 30, 18, 30),
        )
        assert result.created is False
        assert result.path.parent == tmp_path / "vault" / DEFAULT_SUBDIR
        assert "dry run note" in result.body
        # 파일이 실제로 쓰이지 않아야 함
        assert not result.path.exists()

    def test_writes_file_with_default_subdir(self, tmp_path: Path, fresh_repo: Path) -> None:
        vault = tmp_path / "vault"
        result = save_session(
            note="real",
            vault=vault,
            cwd=fresh_repo,
            now=datetime(2026, 4, 30, 18, 30),
        )
        assert result.created
        assert result.path.exists()
        assert result.path.parent == vault / DEFAULT_SUBDIR
        body = result.path.read_text(encoding="utf-8")
        assert body == result.body
        assert "real" in body

    def test_uses_custom_subdir(self, tmp_path: Path, fresh_repo: Path) -> None:
        vault = tmp_path / "vault"
        result = save_session(
            note="x",
            vault=vault,
            subdir="01_Inbox",
            cwd=fresh_repo,
        )
        assert result.path.parent == vault / "01_Inbox"

    def test_collision_appends_suffix(self, tmp_path: Path, fresh_repo: Path) -> None:
        vault = tmp_path / "vault"
        first = save_session(
            note="a",
            title="dup",
            vault=vault,
            cwd=fresh_repo,
            now=datetime(2026, 4, 30, 18, 30),
        )
        second = save_session(
            note="b",
            title="dup",
            vault=vault,
            cwd=fresh_repo,
            now=datetime(2026, 4, 30, 18, 30),
        )
        assert first.path != second.path
        assert first.path.exists()
        assert second.path.exists()
        assert second.path.name.endswith("-2.md")

    def test_auto_title_uses_time_and_branch(self, tmp_path: Path, fresh_repo: Path) -> None:
        result = save_session(
            note="t",
            vault=tmp_path / "vault",
            cwd=fresh_repo,
            dry_run=True,
            now=datetime(2026, 4, 30, 18, 30),
        )
        # 자동 제목은 'HHMM <branch>' 형식
        assert "1830" in result.title
