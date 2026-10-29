"""기록 저장 위치와 Markdown 머리말 경계 계약."""

import os
import subprocess
from pathlib import Path

import pytest

# isort: split
from ai_env.core.session_journal import JournalEntry, list_entries, save_entry
from ai_env.core.session_storage import (
    project_directory,
    render_record,
    resolve_root,
    split_record,
)


def test_obsidian_default_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AI_ENV_SESSION_LOG_DIR", raising=False)
    monkeypatch.setenv("OBSIDIAN_BASE", str(tmp_path))
    assert resolve_root() == tmp_path / "00_session"


def test_worktrees_share_repository_directory_and_same_names_are_split(tmp_path: Path) -> None:
    root = tmp_path / "logs"
    main = tmp_path / "repo" / "kamek-batch"
    subprocess.run(["git", "init", "-q", str(main)], check=True)
    subprocess.run(
        ["git", "-C", str(main), "commit", "-q", "--allow-empty", "-m", "init"],
        check=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
        },
    )
    worktree = tmp_path / "kamek-batch-CDETEAM-1"
    subprocess.run(
        ["git", "-C", str(main), "worktree", "add", "-q", "-b", "CDETEAM-1", str(worktree)],
        check=True,
    )
    # Jira별 worktree도 같은 저장소 폴더에 모여 도구 간 기록을 함께 본다.
    assert project_directory(worktree, root) == root / "kamek-batch" / "agent-logs"
    save_entry(JournalEntry(cwd=str(worktree), agent="codex", summary="worktree 작업"), root)
    rows = list_entries(main, root)
    assert [(row["cwd"], row["branch"]) for row in rows] == [(str(worktree.resolve()), "CDETEAM-1")]
    # 이름만 같은 다른 저장소는 해시를 붙여 분리한다.
    other = tmp_path / "other" / "kamek-batch"
    other.mkdir(parents=True)
    assert project_directory(other, root).parent.name.startswith("kamek-batch-")
    assert list_entries(other, root) == []


def test_values_ending_with_separator_keep_front_matter_boundary() -> None:
    header, body = split_record(render_record({"title": "구분선 ---", "task": "A ---"}, "본문\n"))
    assert "구분선 ---" in header
    assert body == "\n본문\n"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
