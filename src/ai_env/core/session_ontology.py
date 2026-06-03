"""Extract ontology seed records from saved session notes."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .session_save import DEFAULT_SUBDIR

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_HEADING_RE = re.compile(r"^##\s+", re.MULTILINE)


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
    marker = f"## {heading}"
    start = text.find(marker)
    if start < 0:
        return ""
    body_start = text.find("\n", start)
    if body_start < 0:
        return ""
    next_heading = _HEADING_RE.search(text, body_start + 1)
    end = next_heading.start() if next_heading else len(text)
    return text[body_start:end].strip()


def _parse_inline_list(value: str) -> list[str]:
    """Parse `[a, b]` or scalar values into a list."""
    value = value.strip()
    if value == "[]":
        return []
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    if not value:
        return []
    return [item.strip().strip("'\"") for item in value.split(",") if item.strip()]


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
            if child_stripped.startswith(f"- {key}:"):
                break
            if re.match(r"^- [a-z_]+:", child_stripped):
                break
            if child.startswith("  - "):
                values.append(child_stripped[2:].strip())
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
