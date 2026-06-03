#!/usr/bin/env python3
"""Analyze SKILL.md word counts across personal and team skill roots."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ROOTS = (
    "megan-skills/skills",
    "cde-skills/plugins/cde-skills/skills",
    "cde-ranking-skills/.claude/skills",
)


@dataclass(frozen=True)
class SkillTokenStat:
    """Word-count summary for one SKILL.md file."""

    words: int
    name: str
    path: Path


def iter_skill_files(roots: list[Path]) -> list[Path]:
    """Return all SKILL.md files under existing roots."""
    files: list[Path] = []
    for root in roots:
        if root.exists():
            files.extend(sorted(root.rglob("SKILL.md")))
    return files


def count_words(path: Path) -> int:
    """Count whitespace-delimited words in a markdown file."""
    return len(path.read_text(encoding="utf-8", errors="replace").split())


def collect_stats(roots: list[Path]) -> list[SkillTokenStat]:
    """Collect sorted token proxy stats."""
    stats = [
        SkillTokenStat(words=count_words(path), name=path.parent.name, path=path)
        for path in iter_skill_files(roots)
    ]
    return sorted(stats, key=lambda item: item.words, reverse=True)


def render_markdown(stats: list[SkillTokenStat], limit: int) -> str:
    """Render a markdown report."""
    total = sum(item.words for item in stats)
    lines = [
        "# Skill Token Report",
        "",
        f"- skill_count: {len(stats)}",
        f"- total_words: {total}",
        "",
        "| words | skill | path |",
        "|---:|---|---|",
    ]
    for item in stats[:limit]:
        lines.append(f"| {item.words} | {item.name} | `{item.path}` |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", action="append", default=None, help="Skill root to scan")
    parser.add_argument("--limit", type=int, default=40)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    roots = [Path(root) for root in (args.root or DEFAULT_ROOTS)]
    report = render_markdown(collect_stats(roots), args.limit)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report, encoding="utf-8")
    else:
        print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
