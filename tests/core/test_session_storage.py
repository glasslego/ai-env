"""기록 저장 위치와 Markdown 머리말 경계 계약."""

from pathlib import Path

import pytest

# isort: split
from ai_env.core.session_storage import render_record, resolve_root, split_record


def test_obsidian_default_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AI_ENV_SESSION_LOG_DIR", raising=False)
    monkeypatch.setenv("OBSIDIAN_BASE", str(tmp_path))
    assert resolve_root() == tmp_path / "00_session" / "agent-logs"


def test_values_ending_with_separator_keep_front_matter_boundary() -> None:
    header, body = split_record(render_record({"title": "구분선 ---", "task": "A ---"}, "본문\n"))
    assert "구분선 ---" in header
    assert body == "\n본문\n"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
