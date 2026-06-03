"""Tests for session ontology extraction script rendering."""

from __future__ import annotations

import json
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType

from ai_env.core.session_ontology import SessionOntologyRecord


def _load_script_module() -> ModuleType:
    script_path = Path(__file__).parents[2] / "scripts" / "extract_session_ontology.py"
    spec = spec_from_file_location("extract_session_ontology_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


SCRIPT = _load_script_module()


def test_render_jsonl_serializes_source_path(tmp_path: Path) -> None:
    record = SessionOntologyRecord(source=tmp_path / "session.md", entities=["Codex"])

    rendered = SCRIPT.render_jsonl([record])
    data = json.loads(rendered)

    assert data["source"] == str(tmp_path / "session.md")
    assert data["entities"] == ["Codex"]


def test_render_markdown_escapes_table_cells(tmp_path: Path) -> None:
    record = SessionOntologyRecord(
        source=tmp_path / "session.md",
        title="ranking|session\nreview",
        project="ai-env",
        branch="feature",
        entities=["Gift|Ranking", "ForMe\nSlot"],
    )

    rendered = SCRIPT.render_markdown([record])

    assert "ranking\\|session review" in rendered
    assert "Gift\\|Ranking, ForMe Slot" in rendered
