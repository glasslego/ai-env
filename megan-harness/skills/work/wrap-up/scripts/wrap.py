#!/usr/bin/env python3
"""Build/refresh the daily note for wrap-up.

자동 갱신 영역: ## 오늘의 세션, ## 진행중 Jira, ## 미완 todo (어제 carry-over).
보존 영역: ## 메모, ## 결정사항, ## 내일 (사용자 입력).
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
DIRS = {
    "daily": "90_journal/01_daily",
    "sessions": "90_journal/04_sessions",
    "jira": "1X_업무카카오/jira",
}
PRESERVED_SECTIONS = ("## 메모", "## 결정사항", "## 내일")
SECTION_RE = re.compile(r"^## .+$", re.MULTILINE)
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def resolve_vault(arg: str | None) -> Path:
    if arg:
        return Path(arg).expanduser()
    return Path(os.environ.get("OBSIDIAN_BASE") or DEFAULT_VAULT).expanduser()


def split_sections(body: str) -> dict[str, str]:
    """`## ` 헤더 단위로 본문 분리. 헤더 없는 선두 영역은 ''."""
    sections: dict[str, str] = {}
    matches = list(SECTION_RE.finditer(body))
    if not matches:
        sections[""] = body
        return sections
    if matches[0].start() > 0:
        sections[""] = body[: matches[0].start()]
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        header = m.group(0).rstrip()
        sections[header] = body[m.end() : end]
    return sections


def merge_sections(old: dict[str, str], new: dict[str, str]) -> dict[str, str]:
    """new 의 섹션으로 갱신하되, PRESERVED_SECTIONS 는 old 우선."""
    out: dict[str, str] = {}
    for k, v in new.items():
        if k in PRESERVED_SECTIONS and k in old and old[k].strip():
            out[k] = old[k]
        else:
            out[k] = v
    # old 에만 있는 사용자 추가 섹션도 보존
    for k, v in old.items():
        if k not in out:
            out[k] = v
    return out


def render_body(date: str, weekday: str, sections: dict[str, str]) -> str:
    fm = f"---\ndate: {date}\ntype: daily\ntags: [daily]\n---\n\n"
    head = f"# {date} ({weekday})\n\n"
    parts = [fm, head]
    if "" in sections and sections[""].strip():
        parts.append(sections[""])
    order = [
        "## 오늘의 세션",
        "## 진행중 Jira (자동)",
        "## 미완 todo",
        "## 결정사항",
        "## 메모",
        "## 내일",
    ]
    for h in order:
        if h not in sections:
            continue
        parts.append(f"{h}\n{sections[h].strip()}\n\n")
    for k, v in sections.items():
        if k in ("",) or k in order:
            continue
        parts.append(f"{k}\n{v.strip()}\n\n")
    return "".join(parts).rstrip() + "\n"


def todays_sessions(vault: Path, date: str) -> list[str]:
    sess_dir = vault / DIRS["sessions"]
    if not sess_dir.exists():
        return [f"- (없음 — `{DIRS['sessions']}/` 미발견)"]
    items = []
    for p in sess_dir.rglob(f"{date}-*.md"):
        items.append(f"- `{date}` — [[{p.stem}]]")
    return items or [f"- (없음 — {date} session 노트 미발견)"]


def in_progress_jira(vault: Path) -> list[str]:
    jdir = vault / DIRS["jira"]
    if not jdir.exists():
        return ["- (없음 — jira 폴더 미발견)"]
    out = []
    for p in sorted(jdir.glob("*.md")):
        text = p.read_text(encoding="utf-8", errors="replace")
        m = FRONTMATTER_RE.match(text)
        if not m:
            continue
        fm = m.group(1)
        if not re.search(r"^status:\s*['\"]?In Progress['\"]?\s*$", fm, re.MULTILINE):
            continue
        title_m = re.search(r"^title:\s*(.+)$", fm, re.MULTILINE)
        title = title_m.group(1).strip(" '\"") if title_m else ""
        out.append(f"- **{p.stem}** — {title}")
    return out or ["- (In Progress 없음)"]


def yesterdays_unchecked(vault: Path, date: str) -> list[str]:
    yest = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    p = vault / DIRS["daily"] / f"{yest}.md"
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if re.match(r"^\s*-\s*\[\s\]\s+", line):
            out.append(line.rstrip())
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault")
    ap.add_argument("--date")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    vault = resolve_vault(args.vault)
    if not vault.exists():
        print(f"vault not found: {vault}", file=sys.stderr)
        return 2

    today_dt = datetime.now(KST)
    date = args.date or today_dt.strftime("%Y-%m-%d")
    weekday = (
        today_dt.strftime("%a")
        if not args.date
        else datetime.strptime(args.date, "%Y-%m-%d").strftime("%a")
    )

    daily_dir = vault / DIRS["daily"]
    daily_dir.mkdir(parents=True, exist_ok=True)
    note = daily_dir / f"{date}.md"

    auto = {
        "## 오늘의 세션": "\n".join(todays_sessions(vault, date)),
        "## 진행중 Jira (자동)": "\n".join(in_progress_jira(vault)),
        "## 미완 todo": "\n".join(yesterdays_unchecked(vault, date))
        or "- (어제 daily 없음/모두 완료)",
        "## 결정사항": "- ",
        "## 메모": "_여기에 자유 메모 — wrap-up 갱신 시 보존됨_",
        "## 내일": "- [ ] ",
    }

    if note.exists():
        text = note.read_text(encoding="utf-8")
        m = FRONTMATTER_RE.match(text)
        body = text[m.end() :] if m else text
        old = split_sections(body)
        merged = merge_sections(old, auto)
    else:
        merged = auto

    rendered = render_body(date, weekday, merged)
    if args.dry_run:
        sys.stdout.write(rendered)
        return 0
    note.write_text(rendered, encoding="utf-8")
    print(f"wrap-up: {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
