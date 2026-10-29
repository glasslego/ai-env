"""세션 종료·기간 정리가 원본 보존과 멱등성을 지킨다."""

from pathlib import Path

import pytest

# isort: split
from ai_env.core.session_compaction import compact_entries
from ai_env.core.session_journal import JournalEntry, list_entries, save_entry


def test_session_compaction_preserves_sources_and_repeats_safely(tmp_path: Path) -> None:
    root = tmp_path / "logs"
    source = save_entry(
        JournalEntry(
            cwd=str(tmp_path),
            agent="codex",
            session_id="s",
            turn_id="t",
            kind="checkpoint",
            status="stopped",
            summary="중간 상태: 테스트 실패",
        ),
        root,
    )
    original = Path(source["path"]).read_bytes()
    save_entry(
        JournalEntry(
            cwd=str(tmp_path), agent="claude", session_id="other", turn_id="t", summary="다른 세션"
        ),
        root,
    )
    result = compact_entries(tmp_path, root, session_id="s", agent="codex")
    assert len(result) == 1
    path = Path(result[0]["path"])
    text = path.read_text()
    assert "중간 상태: 테스트 실패" in text
    assert "다른 세션" not in text
    assert Path(source["path"]).stem in text
    assert Path(source["path"]).read_bytes() == original
    assert (
        compact_entries(tmp_path, root, session_id="s", agent="codex")[0]["status"] == "unchanged"
    )
    assert len(list_entries(tmp_path, root, kind="summary")) == 1
    # SessionEnd 재전달로 요약 자체를 다시 압축하지 않는다.
    assert compact_entries(tmp_path, root, older_than_days=7) == []


def test_daily_age_cutoff_dry_run_and_incremental_source(tmp_path: Path) -> None:
    root = tmp_path / "logs"
    assert compact_entries(tmp_path, root, older_than_days=7) == []
    assert not root.exists()
    source = save_entry(
        JournalEntry(
            cwd=str(tmp_path),
            agent="codex",
            session_id="s",
            turn_id="t",
            task="SPEC-017",
            summary="## 검증\npytest 통과\n## TODO\n리뷰 대기",
        ),
        root,
    )
    path = Path(source["path"])
    body = path.read_text()
    created = str(list_entries(tmp_path, root)[0]["created"])
    path.write_text(body.replace(created, "2020-01-01T12:00:00+09:00"))
    assert (
        compact_entries(tmp_path, root, older_than_days=7, dry_run=True)[0]["status"]
        == "would_record"
    )
    assert not list_entries(tmp_path, root, kind="summary")
    results = compact_entries(tmp_path, root, older_than_days=7)
    assert len(results) == 1
    assert "2020-01-01" in Path(results[0]["path"]).read_text()


def _age(path: Path, created: str) -> None:
    """기록 시각을 과거로 옮겨 일별 정리 대상으로 만든다."""
    text = path.read_text()
    current = text.split("created: ", 1)[1].split("\n", 1)[0]
    path.write_text(text.replace(current, created))


def test_daily_summary_is_shared_by_agents_and_skips_summarized_days(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "logs"
    sources = []
    # 하루 기록이 많아도 요약 길이 제한으로 원문 링크가 빠지지 않는다.
    for index in range(60):
        agent = ("codex", "claude")[index % 2]
        result = save_entry(
            JournalEntry(cwd=str(tmp_path), agent=agent, turn_id=str(index), summary="보고 " * 300),
            root,
        )
        sources.append(Path(result["path"]))
        _age(sources[-1], f"'2020-01-01T12:00:{index:02d}+09:00'")
    summary = compact_entries(tmp_path, root, agent="claude", archive=True)[0]["path"]
    assert all(f"[[{source.stem}]]" in Path(summary).read_text() for source in sources)
    # 요약이 끝난 날짜는 보관 원문을 다시 풀지 않고 다른 도구도 같은 요약을 쓴다.
    monkeypatch.setattr(
        "ai_env.core.session_compaction.read_entry_text",
        lambda _: pytest.fail("summarized day re-read"),
    )
    assert compact_entries(tmp_path, root, agent="codex", archive=True)[0]["status"] == "unchanged"
    assert len(list_entries(tmp_path, root, kind="summary")) == 1


def test_resumed_session_summarizes_only_new_records(tmp_path: Path) -> None:
    root = tmp_path / "logs"

    def stop(turn: str) -> None:
        save_entry(
            JournalEntry(
                cwd=str(tmp_path), agent="claude", session_id="s", turn_id=turn, summary=turn
            ),
            root,
        )

    stop("첫-턴")
    compact_entries(tmp_path, root, session_id="s", agent="claude")
    stop("재개-턴")
    second = Path(compact_entries(tmp_path, root, session_id="s", agent="claude")[0]["path"])
    assert "재개-턴" in second.read_text()
    assert "첫-턴" not in second.read_text()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
