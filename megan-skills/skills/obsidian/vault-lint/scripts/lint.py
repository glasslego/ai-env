#!/usr/bin/env python3
"""Vault lint: broken wikilinks, orphan notes, missing frontmatter.

Origin: jackie-skills/vault-lint. Simplified for PARA layout.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))
DEFAULT_VAULT = Path.home() / "Documents" / "Obsidian Vault"

# orphan 검사 제외 폴더 (megan vault 컨벤션). path part 기준 매칭이라
# `90_journal/01_daily/...` 도 `90_journal` 매칭으로 제외된다.
ORPHAN_EXEMPT_DIRS = {
    "_meta",
    "90_journal",
    "99_archive",
    "attachments",
    "Excalidraw",
    "templates",
    "scripts",
}
# strict frontmatter 요구 폴더 (top-level part 기준)
STRICT_FRONTMATTER_TOP = {"1X_업무카카오"}
# Obsidian wikilink target 으로 자주 등장하는 첨부 확장자
ATTACHMENT_EXTS = {
    # 이미지/미디어
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".mp4",
    ".mov",
    ".mp3",
    ".m4a",
    ".heic",
    # 문서
    ".pdf",
    ".pptx",
    ".ppt",
    ".xlsx",
    ".xls",
    ".docx",
    ".doc",
    ".csv",
    ".key",
    # Obsidian/디자인
    ".excalidraw",
    ".canvas",
}
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:\|[^\]]+)?\]\]")
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def resolve_vault(arg: str | None) -> Path:
    if arg:
        return Path(arg).expanduser()
    env = os.environ.get("OBSIDIAN_BASE")
    if env:
        return Path(env).expanduser()
    return DEFAULT_VAULT


def is_in_exempt(path: Path, vault: Path) -> bool:
    rel = path.relative_to(vault)
    return any(part in ORPHAN_EXEMPT_DIRS for part in rel.parts)


def collect_notes(vault: Path) -> list[Path]:
    """lint 대상: .md 만 (frontmatter / orphan / wikilink 스캔).

    `_meta/` 는 megan-skills 가 만든 메타 파일(hot.md, lint-report-*.md) 모음이라
    wikilink 자체 증폭(self-amplification)을 피하기 위해 제외한다.
    """
    out: list[Path] = []
    for p in vault.rglob("*.md"):
        if ".obsidian" in p.parts:
            continue
        if "_meta" in p.parts:
            continue
        out.append(p)
    return out


def collect_indexable(vault: Path) -> list[Path]:
    """wikilink target 매칭 인덱스: .md + 첨부 확장자 (Obsidian 동작과 일치)."""
    out: list[Path] = []
    for p in vault.rglob("*"):
        if not p.is_file() or ".obsidian" in p.parts:
            continue
        suf = p.suffix.lower()
        if suf == ".md" or suf in ATTACHMENT_EXTS:
            out.append(p)
    return out


def build_index(files: list[Path]) -> dict[str, list[Path]]:
    """stem 과 full name 양쪽으로 색인. Obsidian 은 `[[Note]]` 와 `[[Note.png]]` 모두 허용."""
    idx: dict[str, list[Path]] = {}
    for p in files:
        idx.setdefault(p.stem, []).append(p)
        idx.setdefault(p.name, []).append(p)
    return idx


def lint(vault: Path) -> dict[str, list[str]]:
    notes = collect_notes(vault)
    indexable = collect_indexable(vault)
    name_idx = build_index(indexable)
    referenced: set[str] = set()
    seen_broken: set[tuple[str, str]] = set()
    broken: list[str] = []
    missing_fm: list[str] = []

    for note in notes:
        rel = note.relative_to(vault)
        try:
            text = note.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        if not FRONTMATTER_RE.match(text):
            top = rel.parts[0] if rel.parts else ""
            if top in STRICT_FRONTMATTER_TOP:
                missing_fm.append(str(rel))

        for m in WIKILINK_RE.finditer(text):
            target = m.group(1).strip()
            # path-style wikilink (e.g. "20_tech/Note") → 마지막 컴포넌트로 매칭
            basename = target.rsplit("/", 1)[-1]
            referenced.add(basename)
            stem = Path(basename).stem
            if stem:
                referenced.add(stem)
            if basename not in name_idx and stem not in name_idx:
                key = (str(rel), target)
                if key in seen_broken:
                    continue
                seen_broken.add(key)
                broken.append(f"{rel} — `[[{target}]]` 미발견")

    orphans: list[str] = []
    for note in notes:
        if is_in_exempt(note, vault):
            continue
        if note.stem not in referenced and note.name not in referenced:
            orphans.append(str(note.relative_to(vault)))

    return {
        "broken_wikilinks": broken,
        "orphan_notes": orphans,
        "missing_frontmatter": missing_fm,
    }


def render_report(result: dict[str, list[str]], max_orphans: int) -> str:
    today = datetime.now(KST).strftime("%Y-%m-%d")
    lines = [f"# Vault Lint — {today}", "", "| Category | Count |", "|---|---|"]
    for k, v in result.items():
        lines.append(f"| {k.replace('_', ' ')} | {len(v)} |")
    lines.append("")
    for k, v in result.items():
        lines.append(f"## {k.replace('_', ' ').title()}")
        if not v:
            lines.append("- (없음)")
        else:
            cap = max_orphans if k == "orphan_notes" else len(v)
            for item in v[:cap]:
                lines.append(f"- {item}")
            if len(v) > cap:
                lines.append(f"- … (+{len(v) - cap} more)")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault")
    ap.add_argument("--report-only", action="store_true")
    ap.add_argument("--max-orphans", type=int, default=50)
    args = ap.parse_args()

    vault = resolve_vault(args.vault)
    if not vault.exists():
        print(f"vault not found: {vault}", file=sys.stderr)
        return 2

    result = lint(vault)
    report = render_report(result, args.max_orphans)
    meta = vault / "_meta"
    meta.mkdir(parents=True, exist_ok=True)
    out = meta / f"lint-report-{datetime.now(KST).strftime('%Y-%m-%d')}.md"
    out.write_text(report, encoding="utf-8")

    if not args.report_only:
        counts = {k: len(v) for k, v in result.items()}
        print(
            f"vault lint: broken={counts['broken_wikilinks']} "
            f"orphans={counts['orphan_notes']} "
            f"missing_fm={counts['missing_frontmatter']} → {out}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
