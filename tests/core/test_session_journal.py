"""공용 기록의 격리·불변성·동시 저장 계약."""

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

# isort: split
from ai_env.core.session_journal import JournalEntry, list_entries, save_entry
from ai_env.core.session_storage import project_directory


def entry(project: Path, **changes: str) -> JournalEntry:
    """서로 다른 에이전트가 생성하는 기록 입력."""
    return JournalEntry(cwd=str(project), agent="codex", summary="구현 및 검증 완료", **changes)


def test_isolation_dry_run_and_permissions(tmp_path: Path) -> None:
    root = tmp_path / "logs"
    one, two = tmp_path / "one" / "app", tmp_path / "two" / "app"
    one.mkdir(parents=True)
    two.mkdir(parents=True)
    preview = save_entry(entry(one), root, dry_run=True)
    assert not root.exists()
    assert preview["status"] == "would_record"
    result = save_entry(entry(one, request='메모에 "따옴표"\n추가'), root)
    path = Path(result["path"])
    assert path.name.startswith("codex__unclassified__app__work__")
    assert path.stat().st_mode & 0o777 == 0o600
    assert path.parent.stat().st_mode & 0o777 == 0o700
    assert len(list_entries(one, root)) == 1
    assert list_entries(two, root) == []


def test_idempotency_turns_concurrency_and_parent(tmp_path: Path) -> None:
    root = tmp_path / "logs"
    source = entry(tmp_path, session_id="s", turn_id="t")
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda _: save_entry(source, root), range(8)))
    assert len({result["path"] for result in results}) == 1
    assert sum(result["status"] == "recorded" for result in results) == 1
    parent = results[0]["path"]
    save_entry(entry(tmp_path, session_id="s", turn_id="t2"), root)
    review = JournalEntry(
        cwd=str(tmp_path),
        agent="claude",
        kind="review",
        task="SPEC-017",
        parent=parent,
        summary="指摘",
        status="changes-requested",
    )
    result = save_entry(review, root)
    assert len(list_entries(tmp_path, root)) == 3
    hits = list_entries(tmp_path, root, agent="claude", kind="review", task="SPEC-017")
    assert len(hits) == 1
    assert hits[0]["parent"] == parent
    assert hits[0]["path"] == result["path"]
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    with pytest.raises(ValueError, match="parent"):
        save_entry(entry(foreign, parent=parent), root)


def test_symlink_escape_and_secret_redaction(tmp_path: Path) -> None:
    root = tmp_path / "logs"
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    directory = project_directory(project, root)
    root.mkdir()
    directory.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        save_entry(entry(project), root)
    directory.unlink()
    result = save_entry(
        entry(project, request="TOKEN=private-value Authorization: Bearer hidden-value"), root
    )
    text = Path(result["path"]).read_text()
    assert "private-value" not in text
    assert "hidden-value" not in text
    assert "[REDACTED]" in text
    assert json.dumps(list_entries(project, root))


def test_obsidian_default_jira_branch_scope_and_filename_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("AI_ENV_SESSION_LOG_DIR", raising=False)
    monkeypatch.setenv("OBSIDIAN_BASE", str(tmp_path / "vault"))
    (tmp_path / "vault").mkdir()
    project = tmp_path / ("프로젝트" * 10)
    project.mkdir()
    subprocess.run(
        ["git", "init", "-b", "CDETEAM-1234", str(project)], check=True, capture_output=True
    )
    profile = project / ".claude" / "project-profile.yaml"
    profile.parent.mkdir()
    profile.write_text("project:\n  session_scope: kakao\n")
    result = save_entry(entry(project, title="긴 주제 요약 " * 30, task="SPEC-017/TASK-01"))
    path = Path(result["path"])
    assert path.name.startswith("codex__kakao__")
    assert path.name.count("CDETEAM-1234") == 1
    assert len(path.name.encode()) <= 255
    row = list_entries(project)[0]
    assert row["jira"] == row["branch"] == "CDETEAM-1234"
    assert row["task"] == "SPEC-017/TASK-01"
    assert list_entries(profile.parent)[0]["path"] == str(path)
    # 명시한 Jira가 브랜치와 다르면 모두 남긴다.
    second = save_entry(entry(project, jira="CDETEAM-5678"))
    assert "__CDETEAM-5678__CDETEAM-1234__" in Path(second["path"]).name


def test_obsidian_notes_without_journal_header_are_ignored(tmp_path: Path) -> None:
    root = tmp_path / "logs"
    save_entry(entry(tmp_path), root)
    directory = project_directory(tmp_path, root)
    (directory / "메모.md").write_text("그냥 메모\n")
    (directory / "속성.md").write_text("---\ntags: [memo]\n---\n본문\n")
    assert len(list_entries(tmp_path, root)) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
