#!/usr/bin/env python3
"""Jira ↔ vault note sync (megan vault convention).

이 스크립트는 Jira API 를 **직접 호출하지 않는다**. 다음 의존성 중 하나가
설치/인증된 환경을 가정한다:

  1) cde-skills/development/jira 서브스킬 (glob: ~/.claude/skills/development/jira/scripts)
  2) jira-wiki-mcp (글로벌 MCP)

스크립트는 vault note 의 frontmatter 컨벤션·body 레이아웃을 강제하고,
실제 Jira fetch/update 호출은 위 의존성에 위임한다.

현재 단계는 vault note skeleton 생성 + frontmatter merge 만 구현.
실제 jira_*.py 호출은 후속 단계 (Phase 2.5) — 이 스크립트가 제공하는
contract 가 안정되면 그때 wiring.
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
JIRA_DIR = "1X_업무카카오/jira"
USER_MEMO_HEADER = "## 메모"
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
KEY_RE = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")


def resolve_vault(arg: str | None) -> Path:
    if arg:
        return Path(arg).expanduser()
    return Path(os.environ.get("OBSIDIAN_BASE") or DEFAULT_VAULT).expanduser()


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm: dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm, text[m.end() :]


def render_frontmatter(fm: dict[str, str]) -> str:
    lines = ["---"]
    for k, v in fm.items():
        if v == "" or v is None:
            continue
        lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def extract_user_memo(body: str) -> str:
    idx = body.find(USER_MEMO_HEADER)
    if idx < 0:
        return ""
    return body[idx:].rstrip() + "\n"


def render_skeleton(key: str, fm: dict[str, str], existing_memo: str) -> str:
    title = fm.get("title", "(제목 미정)")
    status = fm.get("status", "Open")
    today = datetime.now(KST).strftime("%Y-%m-%d")
    base_fm = {
        "key": key,
        "title": fm.get("title", ""),
        "status": status,
        "assignee": fm.get("assignee", ""),
        "priority": fm.get("priority", ""),
        "labels": fm.get("labels", "[]"),
        "sprint": fm.get("sprint", ""),
        "created": fm.get("created", today),
        "updated": today,
        "url": fm.get("url", ""),
    }
    body = [
        f"# {key} — {title}",
        "",
        "## 설명",
        fm.get("description", "(Jira description 미동기화 — `--mode pull` 로 갱신 필요)"),
        "",
        "## 진행 상황",
        "(Jira comments 최신 5개 — sync 후 자동 채움)",
        "",
    ]
    if existing_memo:
        body.append(existing_memo.rstrip())
    else:
        body.append(f"{USER_MEMO_HEADER}\n\n_여기에 자유 메모 — sync 시 보존됨._")
    body.append("")
    body.append("## 관련 링크")
    body.append("- ")
    return render_frontmatter(base_fm) + "\n" + "\n".join(body) + "\n"


def jira_dependency_check() -> list[str]:
    """가능한 Jira 백엔드 후보 경로 반환. 비어있으면 의존성 없음."""
    out: list[str] = []
    candidates = [
        Path.home() / ".claude" / "skills" / "development" / "jira" / "scripts",
        Path.home()
        / ".claude"
        / "skills"
        / "cde-skills"
        / "skills"
        / "development"
        / "jira"
        / "scripts",
        Path.home() / "work" / "cde" / "cde-skills" / "skills" / "development" / "jira" / "scripts",
    ]
    for p in candidates:
        if p.exists() and any(p.glob("jira_*.py")):
            out.append(str(p))
            break
    # MCP 등록 여부는 Claude 가 직접 판단 (settings.json 검사는 skill 책임 X)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("key", help="JIRA issue key, e.g. CDE-1234")
    ap.add_argument("--vault")
    ap.add_argument("--mode", choices=["pull", "push", "both", "skeleton"], default="skeleton")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not KEY_RE.match(args.key):
        print(f"invalid key: {args.key}", file=sys.stderr)
        return 2

    vault = resolve_vault(args.vault)
    if not vault.exists():
        print(f"vault not found: {vault}", file=sys.stderr)
        return 2

    note_dir = vault / JIRA_DIR
    note_dir.mkdir(parents=True, exist_ok=True)
    note = note_dir / f"{args.key}.md"

    existing_fm: dict[str, str] = {}
    existing_memo = ""
    if note.exists():
        text = note.read_text(encoding="utf-8")
        existing_fm, body = parse_frontmatter(text)
        existing_memo = extract_user_memo(body)

    if args.mode == "skeleton":
        if note.exists():
            print(f"note exists: {note} (use --mode pull to refresh from Jira)")
            return 0
        rendered = render_skeleton(args.key, existing_fm, existing_memo)
        if args.dry_run:
            sys.stdout.write(rendered)
            return 0
        note.write_text(rendered, encoding="utf-8")
        print(f"created skeleton: {note}")
        return 0

    # pull / push / both: 의존성 안내 후 종료 (Phase 2.5 에서 wiring)
    deps = jira_dependency_check()
    print("Jira API 의존성 체크:")
    if deps:
        print(f"  ✓ cde-skills development/jira 발견: {deps[0]}")
    else:
        print("  ✗ cde-skills development/jira 미발견.")
        print("  대안: jira-wiki-mcp 가 글로벌 MCP 로 등록되어 있으면 Claude 가 호출 가능.")
    print()
    print(f"mode={args.mode} 는 Phase 2.5 에서 wiring 예정.")
    print("현재 단계: vault skeleton 만 생성. 실제 Jira pull/push 는 in-conversation 에서")
    print("위 백엔드를 직접 호출하고, 그 결과를 이 스크립트의 frontmatter 컨벤션에 맞춰 저장.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
