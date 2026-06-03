"""Extract and render ontology seed records from saved session notes."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .session_save import DEFAULT_SUBDIR

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_SECTION_HEADING_RE = re.compile(r"^##\s+(?P<title>.+?)\s*$", re.MULTILINE)
_SEED_KEY_RE = re.compile(r"^-\s+(?P<key>[A-Za-z_][\w-]*):")
_NESTED_ITEM_RE = re.compile(r"^\s+-\s+(?P<value>.+?)\s*$")


@dataclass(frozen=True)
class SessionOntologyRecord:
    """Ontology seed fields extracted from one session note."""

    source: Path
    title: str = ""
    created: str = ""
    project: str = ""
    branch: str = ""
    entities: list[str] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    todos: list[str] = field(default_factory=list)


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Parse simple scalar YAML frontmatter used by session notes."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}

    values: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    return values


def _extract_section(text: str, heading: str) -> str:
    """Extract a level-2 markdown section body by heading text."""
    headings = list(_SECTION_HEADING_RE.finditer(text))
    for index, match in enumerate(headings):
        if match.group("title").strip() != heading:
            continue
        start = match.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        return text[start:end].strip()
    return ""


def _clean_seed_item(value: str) -> str:
    """Normalize one ontology seed item."""
    return value.strip().strip("'\"")


def _parse_inline_list(value: str) -> list[str]:
    """Parse `[a, b]` or scalar values into a list."""
    value = value.strip()
    if value == "[]":
        return []
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    if not value:
        return []
    return [_clean_seed_item(item) for item in value.split(",") if item.strip()]


def _parse_seed_values(section: str, key: str) -> list[str]:
    """Parse one ontology seed key from the `Ontology Seeds` section."""
    lines = section.splitlines()
    values: list[str] = []

    for index, line in enumerate(lines):
        stripped = line.strip()
        prefix = f"- {key}:"
        if not stripped.startswith(prefix):
            continue

        inline = stripped[len(prefix) :].strip()
        values.extend(_parse_inline_list(inline))

        for child in lines[index + 1 :]:
            child_stripped = child.strip()
            if _SEED_KEY_RE.match(child_stripped):
                break
            nested = _NESTED_ITEM_RE.match(child)
            if nested:
                values.append(_clean_seed_item(nested.group("value")))
        break

    return values


def extract_session_ontology(path: Path) -> SessionOntologyRecord:
    """Extract ontology seeds from one markdown session note."""
    text = path.read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    seeds = _extract_section(text, "Ontology Seeds")

    return SessionOntologyRecord(
        source=path,
        title=fm.get("title", ""),
        created=fm.get("created", ""),
        project=fm.get("project", ""),
        branch=fm.get("branch", ""),
        entities=_parse_seed_values(seeds, "entities"),
        tools=_parse_seed_values(seeds, "tools"),
        decisions=_parse_seed_values(seeds, "decisions"),
        todos=_parse_seed_values(seeds, "todos"),
    )


def collect_session_ontology(
    vault: Path, subdir: str = DEFAULT_SUBDIR
) -> list[SessionOntologyRecord]:
    """Collect ontology seed records from an Obsidian session directory."""
    session_dir = vault.expanduser() / subdir
    if not session_dir.is_dir():
        return []
    return [extract_session_ontology(path) for path in sorted(session_dir.glob("*.md"))]


def _record_to_jsonable(record: SessionOntologyRecord) -> dict[str, Any]:
    """Convert a record to a JSON-serializable dictionary."""
    data = asdict(record)
    data["source"] = str(record.source)
    return data


def render_session_ontology_jsonl(records: list[SessionOntologyRecord]) -> str:
    """Render ontology seed records as JSONL."""
    return "\n".join(
        json.dumps(_record_to_jsonable(record), ensure_ascii=False) for record in records
    ) + ("\n" if records else "")


def _markdown_cell(value: str) -> str:
    """Escape a value for a compact markdown table cell."""
    normalized = value.replace("\r\n", "\n").replace("\r", "\n").replace("\n", " ")
    return normalized.replace("|", r"\|").strip()


def _markdown_list_cell(values: list[str]) -> str:
    """Render list values as one escaped markdown table cell."""
    return _markdown_cell(", ".join(values))


def render_session_ontology_markdown(records: list[SessionOntologyRecord]) -> str:
    """Render ontology seed records as a compact markdown table."""
    lines = [
        "# Session Ontology Seeds",
        "",
        "| created | project | branch | title | entities | tools | decisions | todos |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for record in records:
        cells = [
            _markdown_cell(record.created),
            _markdown_cell(record.project),
            _markdown_cell(record.branch),
            _markdown_cell(record.title),
            _markdown_list_cell(record.entities),
            _markdown_list_cell(record.tools),
            _markdown_list_cell(record.decisions),
            _markdown_list_cell(record.todos),
        ]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"
