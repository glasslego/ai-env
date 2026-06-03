"""Tests for session ontology extraction."""

from __future__ import annotations

import json
from pathlib import Path

from ai_env.core.session_ontology import (
    SessionOntologyRecord,
    collect_session_ontology,
    extract_session_ontology,
    render_session_ontology_jsonl,
    render_session_ontology_markdown,
)


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


def test_extract_session_ontology_uses_exact_heading_and_flexible_indent(
    tmp_path: Path,
) -> None:
    note = tmp_path / "session.md"
    note.write_text(
        """## Ontology Seeds Extra

- entities: [Wrong]

## Ontology Seeds

- entities:
    - "ForMe Slot"
    - 'Gift Ranking'
- tools: [codex]

## Next

- entities: [Ignored]
""",
        encoding="utf-8",
    )

    record = extract_session_ontology(note)

    assert record.entities == ["ForMe Slot", "Gift Ranking"]
    assert record.tools == ["codex"]


def test_collect_session_ontology(tmp_path: Path) -> None:
    session_dir = tmp_path / "00_Sessions"
    session_dir.mkdir()
    (session_dir / "a.md").write_text("## Ontology Seeds\n\n- entities: [A]\n", encoding="utf-8")
    (session_dir / "b.md").write_text("## Ontology Seeds\n\n- entities: [B]\n", encoding="utf-8")

    records = collect_session_ontology(tmp_path)

    assert [record.entities for record in records] == [["A"], ["B"]]


def test_render_session_ontology_jsonl_and_markdown_escape(tmp_path: Path) -> None:
    record = SessionOntologyRecord(
        source=tmp_path / "session.md",
        title="ranking|session\nreview",
        project="ai-env",
        branch="feature",
        entities=["Gift|Ranking", "ForMe\nSlot"],
    )

    jsonl = render_session_ontology_jsonl([record])
    data = json.loads(jsonl)
    markdown = render_session_ontology_markdown([record])

    assert data["source"] == str(tmp_path / "session.md")
    assert data["entities"] == ["Gift|Ranking", "ForMe\nSlot"]
    assert "ranking\\|session review" in markdown
    assert "Gift\\|Ranking, ForMe Slot" in markdown
