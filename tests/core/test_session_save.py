"""ai_env.core.session_save 단위 테스트."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

import pytest
from ai_env.core.session_save import (
    DEFAULT_SUBDIR,
    GitSnapshot,
    _next_available_path,
    build_latest_session_context,
    build_session_note,
    collect_git_snapshot,
    compress_transcript,
    find_latest_session,
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

    def test_auto_title_uses_project_and_branch(self, tmp_path: Path, fresh_repo: Path) -> None:
        result = save_session(
            note="t",
            vault=tmp_path / "vault",
            cwd=fresh_repo,
            dry_run=True,
            now=datetime(2026, 4, 30, 18, 30),
        )
        assert result.title.startswith("repo session ")
        assert result.path.name.startswith("2026-04-30 18 repo-session-")

    def test_auto_filename_uses_date_hour_project_session_prefix(
        self,
        tmp_path: Path,
        fresh_repo: Path,
    ) -> None:
        result = save_session(
            note="t",
            vault=tmp_path / "vault",
            cwd=fresh_repo,
            session_id="abcdef123456",
            agent="claude",
            dry_run=True,
            now=datetime(2026, 4, 30, 18, 30),
        )
        assert result.title == "repo session abcdef12"
        assert result.path.name == "2026-04-30 18 repo-session-abcdef12.md"
        assert "session_id: abcdef123456" in result.body
        assert "agent: claude" in result.body

    def test_transcript_summary_is_embedded(self, tmp_path: Path, fresh_repo: Path) -> None:
        transcript = tmp_path / "session.jsonl"
        events = [
            {
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": "src/ai_env/core/session_save.py 고쳐줘"}],
                }
            },
            {
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "세션 압축 저장을 추가하기로 결정"}],
                }
            },
            {
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "functions.exec_command",
                            "input": {"cmd": "uv run pytest tests/core/test_session_save.py"},
                        }
                    ],
                }
            },
            {
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_result",
                            "is_error": True,
                            "content": "ERROR: one test failed",
                        }
                    ],
                }
            },
        ]
        transcript.write_text(
            "\n".join(json.dumps(event, ensure_ascii=False) for event in events),
            encoding="utf-8",
        )

        result = save_session(
            note="with transcript",
            vault=tmp_path / "vault",
            cwd=fresh_repo,
            transcript_path=transcript,
            dry_run=True,
            now=datetime(2026, 4, 30, 18, 30),
        )

        assert "### Compressed Conversation" in result.body
        assert "### User Requests" in result.body
        assert "src/ai_env/core/session_save.py" in result.body
        assert "functions.exec_command" in result.body
        assert "ERROR: one test failed" in result.body


class TestTranscriptCompression:
    def test_compress_transcript_returns_empty_for_missing_file(self, tmp_path: Path) -> None:
        assert compress_transcript(tmp_path / "missing.jsonl") == ""

    def test_compress_transcript_extracts_context(self, tmp_path: Path) -> None:
        transcript = tmp_path / "codex.jsonl"
        transcript.write_text(
            "\n".join(
                [
                    json.dumps({"role": "user", "content": "README.md 문서 업데이트해줘"}),
                    json.dumps(
                        {
                            "role": "assistant",
                            "content": [
                                {"type": "text", "text": "README.md와 src/app.py를 확인함"},
                                {
                                    "type": "tool_use",
                                    "name": "functions.exec_command",
                                    "input": {"cmd": "rg session README.md"},
                                },
                            ],
                        }
                    ),
                ]
            ),
            encoding="utf-8",
        )

        body = compress_transcript(transcript)
        assert "### User Requests" in body
        assert "README.md" in body
        assert "src/app.py" in body
        assert "functions.exec_command" in body


class TestLatestSession:
    def test_find_latest_session_filters_by_project(self, tmp_path: Path, fresh_repo: Path) -> None:
        vault = tmp_path / "vault"
        first = save_session(
            note="old",
            vault=vault,
            cwd=fresh_repo,
            session_id="11111111",
            now=datetime(2026, 4, 30, 18, 0),
        )
        second = save_session(
            note="new",
            vault=vault,
            cwd=fresh_repo,
            session_id="22222222",
            now=datetime(2026, 4, 30, 19, 0),
        )
        other_repo = tmp_path / "other"
        other_repo.mkdir()
        other = save_session(
            note="other",
            vault=vault,
            cwd=other_repo,
            session_id="33333333",
            now=datetime(2026, 4, 30, 20, 0),
        )
        os.utime(first.path, (1000, 1000))
        os.utime(second.path, (2000, 2000))
        os.utime(other.path, (3000, 3000))

        result = find_latest_session(vault=vault, cwd=fresh_repo)

        assert result.found is True
        assert result.path == second.path
        assert "new" in result.body

    def test_build_latest_session_context_renders_header(
        self,
        tmp_path: Path,
        fresh_repo: Path,
    ) -> None:
        vault = tmp_path / "vault"
        saved = save_session(
            note="latest context",
            vault=vault,
            cwd=fresh_repo,
            session_id="abcdef12",
            now=datetime(2026, 4, 30, 18, 0),
        )

        result = build_latest_session_context(vault=vault, cwd=fresh_repo)

        assert result.found is True
        assert result.path == saved.path
        assert "# Latest Session Context: repo" in result.body
        assert str(saved.path) in result.body
        assert "latest context" in result.body
