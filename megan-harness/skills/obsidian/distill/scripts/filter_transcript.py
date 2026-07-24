#!/usr/bin/env python3
"""Filter a session jsonl transcript to user/assistant text only.

Origin: jackie-skills/distill. No external LLM call — produces a clean
plain-text turn stream for in-conversation distillation.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

KST = timezone(timedelta(hours=9))
DEFAULT_VAULT = Path.home() / "Documents" / "Obsidian Vault"
ARCHIVE_SUBDIR = "99_archive/sessions"


def resolve_vault() -> Path:
    env = os.environ.get("OBSIDIAN_BASE")
    return Path(env).expanduser() if env else DEFAULT_VAULT


def find_jsonl(arg: str | None, latest: bool) -> Path | None:
    arch = resolve_vault() / ARCHIVE_SUBDIR
    if latest:
        candidates = list(arch.rglob("*.jsonl")) if arch.exists() else []
        if not candidates:
            return None
        return max(candidates, key=lambda p: p.stat().st_mtime)
    if arg is None:
        return None
    p = Path(arg).expanduser()
    if p.is_file():
        return p
    if arch.exists():
        for c in arch.rglob(f"{arg}*.jsonl"):
            return c
    return None


def extract_text(event: dict[str, Any]) -> tuple[str, str] | None:
    """Return (role, text) or None for events to skip."""
    role = event.get("role") or event.get("type")
    if role not in ("user", "assistant"):
        return None
    content = event.get("content") or event.get("message", {}).get("content")
    if isinstance(content, str):
        return role, content
    if isinstance(content, list):
        parts = []
        for blk in content:
            if not isinstance(blk, dict):
                continue
            if blk.get("type") in ("tool_use", "tool_result"):
                continue
            text = blk.get("text")
            if text:
                parts.append(text)
        if not parts:
            return None
        return role, "\n".join(parts)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", nargs="?")
    ap.add_argument("--latest", action="store_true")
    ap.add_argument("--turn-limit", type=int, default=100)
    ap.add_argument("--turn-bytes", type=int, default=2048)
    ap.add_argument("--utc-to-kst", action="store_true")
    args = ap.parse_args()

    src = find_jsonl(args.input, args.latest)
    if src is None:
        print("transcript not found", file=sys.stderr)
        return 2

    turns: list[tuple[str, str, str]] = []
    first_ts = None
    with src.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = ev.get("timestamp") or ""
            if first_ts is None and ts:
                first_ts = ts
            extracted = extract_text(ev)
            if extracted is None:
                continue
            role, text = extracted
            text = text[: args.turn_bytes]
            turns.append((ts, role, text))

    if len(turns) > args.turn_limit:
        turns = turns[-args.turn_limit :]

    if args.utc_to_kst and first_ts:
        try:
            dt = datetime.fromisoformat(first_ts.replace("Z", "+00:00"))
            kst = dt.astimezone(KST)
            print(f"# Source: {src.name}")
            print(f"# Started (KST): {kst.strftime('%Y-%m-%d %H:%M')}")
            print()
        except ValueError:
            pass

    for _, role, text in turns:
        prefix = "USER:" if role == "user" else "ASSISTANT:"
        print(prefix)
        print(text.strip())
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
