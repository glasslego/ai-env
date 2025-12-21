"""Helpers for Codex-compatible skill packaging."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_FRONTMATTER_PATTERN = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def _extract_frontmatter_value(frontmatter: str, key: str) -> list[str]:
    """Extract a loose frontmatter value as normalized lines."""
    lines = frontmatter.splitlines()
    target_prefix = f"{key}:"

    for index, line in enumerate(lines):
        if not line.startswith(target_prefix):
            continue

        raw_value = line.split(":", 1)[1].strip()
        value_lines: list[str] = []

        if raw_value and raw_value != "|":
            value_lines.append(raw_value)

        for next_line in lines[index + 1 :]:
            if re.match(r"^[A-Za-z0-9_-]+:\s*", next_line):
                break
            stripped = next_line.strip()
            if stripped:
                value_lines.append(stripped)

        return value_lines

    return []


def _extract_description_from_body(body: str, skill_name: str) -> str:
    """Fallback description extraction from document body."""
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        return stripped
    return skill_name


def normalize_skill_markdown_for_codex(content: str, skill_name: str) -> str:
    """Normalize a SKILL.md file into strict YAML frontmatter for Codex."""
    match = _FRONTMATTER_PATTERN.match(content)
    if match:
        frontmatter = match.group(1)
        body = content[match.end() :].lstrip("\n")
        name_lines = _extract_frontmatter_value(frontmatter, "name")
        description_lines = _extract_frontmatter_value(frontmatter, "description")
        name = name_lines[0] if name_lines else skill_name
        description = "\n".join(description_lines) if description_lines else skill_name
    else:
        body = content.lstrip("\n")
        name = skill_name
        description = _extract_description_from_body(body, skill_name)

    normalized_frontmatter = yaml.safe_dump(
        {"name": name, "description": description},
        allow_unicode=True,
        sort_keys=False,
    ).strip()

    normalized_parts = ["---", normalized_frontmatter, "---", ""]
    normalized_body = body.rstrip()
    if normalized_body:
        normalized_parts.append(normalized_body)
        normalized_parts.append("")

    return "\n".join(normalized_parts)


def copy_skill_tree_for_codex(source: Path, target: Path) -> None:
    """Copy a skill directory or skills root and normalize every SKILL.md file."""
    from .sync import safe_copytree

    safe_copytree(source, target)

    for skill_md in target.rglob("SKILL.md"):
        normalized = normalize_skill_markdown_for_codex(
            skill_md.read_text(encoding="utf-8"),
            skill_md.parent.name,
        )
        skill_md.write_text(normalized, encoding="utf-8")
