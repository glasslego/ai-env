"""Tests for session ontology extraction."""

from __future__ import annotations

from pathlib import Path

from ai_env.core.session_ontology import collect_session_ontology, extract_session_ontology


def test_extract_session_ontology_inline_lists(tmp_path: Path) -> None:
    note = tmp_path / "session.md"
    note.write_text(
        """---
title: harness session
created: 2026-06-03 15:00
project: ai-env
branch: feature
---

# harness session

## Ontology Seeds

- entities: [Codex, Claude Code, megan-skills]
- tools: [uv, pytest]
- decisions: [keep wrappers thin]
- todos: [compact ranking references]
""",
        encoding="utf-8",
    )

    record = extract_session_ontology(note)

    assert record.title == "harness session"
    assert record.project == "ai-env"
    assert record.entities == ["Codex", "Claude Code", "megan-skills"]
    assert record.tools == ["uv", "pytest"]
    assert record.decisions == ["keep wrappers thin"]
    assert record.todos == ["compact ranking references"]


def test_extract_session_ontology_nested_lists(tmp_path: Path) -> None:
    note = tmp_path / "session.md"
    note.write_text(
        """---
title: nested
---

## Ontology Seeds

- entities:
  - ForMe
  - ranking-data-verify
- tools: []
- decisions:
  - delegate to cde-ranking-skills
- todos: []
""",
        encoding="utf-8",
    )

    record = extract_session_ontology(note)

    assert record.entities == ["ForMe", "ranking-data-verify"]
    assert record.tools == []
    assert record.decisions == ["delegate to cde-ranking-skills"]


def test_collect_session_ontology(tmp_path: Path) -> None:
    session_dir = tmp_path / "00_Sessions"
    session_dir.mkdir()
    (session_dir / "a.md").write_text("## Ontology Seeds\n\n- entities: [A]\n", encoding="utf-8")
    (session_dir / "b.md").write_text("## Ontology Seeds\n\n- entities: [B]\n", encoding="utf-8")

    records = collect_session_ontology(tmp_path)

    assert [record.entities for record in records] == [["A"], ["B"]]
