#!/usr/bin/env python3
"""Extract ontology seeds from Obsidian session notes."""

from __future__ import annotations

import argparse
from pathlib import Path

from ai_env.core.session_ontology import (
    collect_session_ontology,
    render_session_ontology_jsonl,
    render_session_ontology_markdown,
)
from ai_env.core.session_save import DEFAULT_SUBDIR


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", type=Path, required=True)
    parser.add_argument("--subdir", default=DEFAULT_SUBDIR)
    parser.add_argument("--format", choices=("jsonl", "markdown"), default="jsonl")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    records = collect_session_ontology(args.vault, args.subdir)
    rendered = (
        render_session_ontology_jsonl(records)
        if args.format == "jsonl"
        else render_session_ontology_markdown(records)
    )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
