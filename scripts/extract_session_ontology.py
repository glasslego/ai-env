#!/usr/bin/env python3
"""Extract ontology seeds from Obsidian session notes."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ai_env.core.session_ontology import SessionOntologyRecord, collect_session_ontology
from ai_env.core.session_save import DEFAULT_SUBDIR


def _record_to_jsonable(record: SessionOntologyRecord) -> dict[str, Any]:
    data = asdict(record)
    data["source"] = str(record.source)
    return data


def render_jsonl(records: list[SessionOntologyRecord]) -> str:
    """Render records as JSONL."""
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


def render_markdown(records: list[SessionOntologyRecord]) -> str:
    """Render records as a compact markdown table."""
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--subdir", default=DEFAULT_SUBDIR)
    parser.add_argument("--format", choices=("jsonl", "markdown"), default="jsonl")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    records = collect_session_ontology(args.vault, args.subdir)
    rendered = render_jsonl(records) if args.format == "jsonl" else render_markdown(records)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
