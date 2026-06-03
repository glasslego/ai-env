#!/usr/bin/env python3
"""Build or read <vault>/_meta/hot.md.

Origin: jackie-skills/daily-hot-builder. Adapted for megan vault layout
(dewey-style numeric prefixes, e.g. 90_journal, 1X_업무카카오, 99_archive).

Sources (best-effort, missing dirs OK):
  1. <vault>/<DIRS.sessions>/**/*.md (recent 7 days, top 5)
  2. <vault>/<DIRS.jira>/*.md (frontmatter status: In Progress)
  3. <vault>/<DIRS.daily>/{today}.md (unchecked todo)
  4. ~/.claude/projects/*/memory/MEMORY.md (7-day mtime)

Preserves the "## 직접 메모" section across rebuilds.
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

# vault 내부 디렉토리 매핑 (megan vault 컨벤션). 컨벤션이 바뀌면 여기만 수정.
DIRS = {
    "sessions": "90_journal/04_sessions",
    "daily": "90_journal/01_daily",
    "jira": "1X_업무카카오/jira",
    "meta": "_meta",
}
USER_NOTES_HEADER = "## 직접 메모"


def resolve_vault(arg: str | None) -> Path:
    if arg:
        return Path(arg).expanduser()
    env = os.environ.get("OBSIDIAN_BASE")
    if env:
        return Path(env).expanduser()
    return DEFAULT_VAULT


def read_existing_user_notes(hot_path: Path) -> str:
    if not hot_path.exists():
        return ""
    text = hot_path.read_text(encoding="utf-8")
    idx = text.find(USER_NOTES_HEADER)
    if idx < 0:
        return ""
    return text[idx:].rstrip() + "\n"


def recent_sessions(vault: Path, days: int = 7, limit: int = 5) -> list[str]:
    sess_dir = vault / DIRS["sessions"]
    if not sess_dir.exists():
        return []
    cutoff = datetime.now(KST) - timedelta(days=days)
    items: list[tuple[float, Path]] = []
    for p in sess_dir.rglob("*.md"):
        try:
            mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=KST)
        except OSError:
            continue
        if mtime < cutoff:
            continue
        items.append((p.stat().st_mtime, p))
    items.sort(reverse=True)
    out = []
    for _, p in items[:limit]:
        date = datetime.fromtimestamp(p.stat().st_mtime, tz=KST).strftime("%Y-%m-%d")
        title = p.stem
        tldr = extract_tldr(p)
        link = f"[[{title}]]"
        out.append(f"- `{date}` — {link} — {tldr}")
    return out


def extract_tldr(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    m = re.search(r"(?:^|\n)## TL;DR\n+(.+?)(?=\n##|\Z)", text, re.DOTALL)
    if m:
        first = m.group(1).strip().split("\n", 1)[0]
        return first[:120]
    body = re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)
    for line in body.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return line[:120]
    return ""


def in_progress_jira(vault: Path) -> list[str]:
    jdir = vault / DIRS["jira"]
    if not jdir.exists():
        return []
    out = []
    for p in sorted(jdir.glob("*.md")):
        text = p.read_text(encoding="utf-8", errors="replace")
        m = re.match(r"---\n(.*?)\n---", text, re.DOTALL)
        if not m:
            continue
        fm = m.group(1)
        if not re.search(r"^status:\s*['\"]?In Progress['\"]?\s*$", fm, re.MULTILINE):
            continue
        key = p.stem
        title_m = re.search(r"^title:\s*(.+)$", fm, re.MULTILINE)
        title = title_m.group(1).strip(" '\"") if title_m else ""
        out.append(f"- **{key}** — {title}")
    return out


def todays_unchecked(vault: Path) -> list[str]:
    today = datetime.now(KST).strftime("%Y-%m-%d")
    p = vault / DIRS["daily"] / f"{today}.md"
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if re.match(r"^\s*-\s*\[\s\]\s+", line):
            out.append(line.rstrip())
    return out


def recent_memory_changes(days: int = 7, limit: int = 8) -> list[str]:
    base = Path.home() / ".claude" / "projects"
    if not base.exists():
        return []
    cutoff = datetime.now(KST) - timedelta(days=days)
    items: list[tuple[float, Path]] = []
    for p in base.rglob("memory/*.md"):
        if p.name == "MEMORY.md":
            continue
        try:
            mt = datetime.fromtimestamp(p.stat().st_mtime, tz=KST)
        except OSError:
            continue
        if mt < cutoff:
            continue
        items.append((p.stat().st_mtime, p))
    items.sort(reverse=True)
    return [f"- `{p.name}`" for _, p in items[:limit]]


def render(vault: Path) -> str:
    today = datetime.now(KST).strftime("%Y-%m-%d (%a)")
    ts = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    sections: list[str] = [f"# Hot — {today}", "", f"> 자동 갱신: {ts}.", ""]

    sections.append("## 진행중")
    jira = in_progress_jira(vault)
    sections.extend(jira if jira else [f"- (없음 — `{DIRS['jira']}/*.md` frontmatter status 확인)"])
    sections.append("")

    sections.append("## 최근 세션 (7일)")
    rs = recent_sessions(vault)
    sections.extend(rs if rs else [f"- (없음 — `{DIRS['sessions']}/` 미발견)"])
    sections.append("")

    sections.append("## 미완 todo")
    todos = todays_unchecked(vault)
    sections.extend(todos if todos else ["- (오늘 daily 노트 없음/모두 완료)"])
    sections.append("")

    sections.append("## 최근 메모리 변경 (7일)")
    mem = recent_memory_changes()
    sections.extend(mem if mem else ["- (없음)"])
    sections.append("")
    return "\n".join(sections)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault")
    ap.add_argument("--read", action="store_true", help="갱신 없이 현재 hot.md 출력")
    ap.add_argument("--max-age-hours", type=float, default=12.0)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    vault = resolve_vault(args.vault)
    if not vault.exists():
        print(f"vault not found: {vault}", file=sys.stderr)
        return 2

    meta_dir = vault / DIRS["meta"]
    meta_dir.mkdir(parents=True, exist_ok=True)
    hot = meta_dir / "hot.md"

    if args.read:
        if hot.exists():
            sys.stdout.write(hot.read_text(encoding="utf-8"))
        else:
            print(f"(no hot.md yet at {hot})")
        return 0

    if not args.force and hot.exists():
        age_h = (datetime.now().timestamp() - hot.stat().st_mtime) / 3600
        if age_h < args.max_age_hours:
            sys.stdout.write(hot.read_text(encoding="utf-8"))
            return 0

    user_section = read_existing_user_notes(hot)
    body = render(vault)
    if not user_section:
        user_section = f"{USER_NOTES_HEADER}\n\n_여기에 자유롭게 메모. 빌드가 이 섹션은 보존._\n"
    final = body + "\n" + user_section
    hot.write_text(final, encoding="utf-8")
    sys.stdout.write(final)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
