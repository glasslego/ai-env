"""Obsidian vault에 현재 세션 컨텍스트를 마크다운 노트로 저장.

스킬/대화 도중 호출되어 현재 세션의 핵심 컨텍스트(사용자 노트, git 스냅샷)를
Obsidian PARA vault의 지정 디렉토리에 영구 저장한다.

CLI(`ai-env session save`) 및 `.claude/skills/session-save` 스킬에서 사용한다.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .config import expand_path, load_settings

DEFAULT_VAULT = "~/Documents/Obsidian Vault"
DEFAULT_SUBDIR = "00_session"
MAX_SLUG_SUFFIX_TRIES = 100

_SLUG_CLEAN = re.compile(r"[^a-zA-Z0-9가-힣\-_]+")
_SLUG_DASHES = re.compile(r"-{2,}")


@dataclass
class SessionSaveResult:
    """세션 저장 결과."""

    path: Path
    title: str
    body: str
    created: bool = True


@dataclass
class GitSnapshot:
    """현재 git 작업 트리 상태 스냅샷."""

    branch: str = ""
    status: str = ""
    log: str = ""
    diff_stat: str = ""
    is_repo: bool = False


def _run_git(args: list[str], cwd: Path) -> str:
    """git 명령 실행. 실패 시 빈 문자열 반환."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
        return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def collect_git_snapshot(cwd: Path | None = None) -> GitSnapshot:
    """현재 디렉토리의 git 상태 스냅샷 수집.

    Args:
        cwd: git 명령을 실행할 디렉토리 (None이면 현재 작업 디렉토리)

    Returns:
        GitSnapshot 객체
    """
    cwd = cwd or Path.cwd()
    snap = GitSnapshot()

    is_repo = _run_git(["rev-parse", "--is-inside-work-tree"], cwd)
    if is_repo != "true":
        return snap

    snap.is_repo = True
    snap.branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
    snap.status = _run_git(["status", "--short"], cwd)
    snap.log = _run_git(["log", "--oneline", "-5"], cwd)
    snap.diff_stat = _run_git(["diff", "--stat"], cwd)
    return snap


def slugify(text: str, *, max_len: int = 60) -> str:
    """Obsidian 파일명에 적합한 slug 생성.

    - 공백 → `-`
    - 한글, 영문, 숫자, `-`, `_` 외 문자는 제거
    - 연속된 `-`는 단일 `-`로 축소
    - 최대 길이 제한
    """
    text = text.strip().replace(" ", "-")
    text = _SLUG_CLEAN.sub("", text)
    text = _SLUG_DASHES.sub("-", text).strip("-_")
    if not text:
        text = "session"
    return text[:max_len]


def _resolve_vault(vault: Path | str | None) -> Path:
    """vault 경로 결정 (인자 → settings.yaml → 기본값)."""
    if vault is not None:
        return expand_path(str(vault))

    try:
        settings = load_settings()
        configured = getattr(settings, "obsidian_base", None)
        if configured:
            return expand_path(configured)
    except Exception:
        # settings.yaml 누락/파싱 실패 시 기본값 사용
        pass

    return expand_path(DEFAULT_VAULT)


def _next_available_path(directory: Path, base_name: str, ext: str = ".md") -> Path:
    """slug 충돌 시 -2, -3 suffix를 붙여 사용 가능한 경로 반환."""
    candidate = directory / f"{base_name}{ext}"
    if not candidate.exists():
        return candidate

    for suffix in range(2, MAX_SLUG_SUFFIX_TRIES + 1):
        candidate = directory / f"{base_name}-{suffix}{ext}"
        if not candidate.exists():
            return candidate

    raise FileExistsError(f"Too many existing notes with prefix '{base_name}' in {directory}")


def _format_frontmatter(values: dict[str, object]) -> str:
    """간단한 YAML frontmatter 직렬화.

    리스트는 `[a, b]` 형식으로, 그 외는 단순 key: value로 출력한다.
    Obsidian이 읽기에 충분한 수준의 단순 직렬화이며 외부 의존성을 추가하지 않는다.
    """
    lines = ["---"]
    for key, value in values.items():
        if value is None or value == "":
            continue
        if isinstance(value, list):
            joined = ", ".join(str(v) for v in value)
            lines.append(f"{key}: [{joined}]")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines)


def build_session_note(
    *,
    title: str,
    note: str | None,
    snapshot: GitSnapshot,
    extras: dict[str, str] | None = None,
    project_name: str | None = None,
    now: datetime | None = None,
) -> str:
    """세션 노트 본문(마크다운) 생성."""
    now = now or datetime.now()
    fm = _format_frontmatter(
        {
            "title": title,
            "created": now.strftime("%Y-%m-%d %H:%M"),
            "tags": ["session", "ai-env"],
            "project": project_name or "",
            "branch": snapshot.branch,
        }
    )

    parts: list[str] = [fm, "", f"# {title}", ""]

    if note:
        parts.extend(["## Note", "", note.strip(), ""])

    if snapshot.is_repo:
        parts.append("## Git Snapshot")
        parts.append("")
        parts.append("```")
        parts.append(f"branch: {snapshot.branch or '(detached)'}")
        if snapshot.status:
            parts.append("")
            parts.append("status:")
            parts.append(snapshot.status)
        if snapshot.log:
            parts.append("")
            parts.append("recent commits:")
            parts.append(snapshot.log)
        parts.append("```")
        parts.append("")

        if snapshot.diff_stat:
            parts.append("## Recent Changes")
            parts.append("")
            parts.append("```")
            parts.append(snapshot.diff_stat)
            parts.append("```")
            parts.append("")

    if extras:
        parts.append("## Extras")
        parts.append("")
        for key, value in extras.items():
            parts.append(f"### {key}")
            parts.append("")
            parts.append(value.rstrip())
            parts.append("")

    parts.append("## Ontology Seeds")
    parts.append("")
    parts.append("- entities: []")
    parts.append("- tools: []")
    parts.append("- decisions: []")
    parts.append("- todos: []")
    parts.append("")

    return "\n".join(parts).rstrip() + "\n"


def save_session(
    *,
    note: str | None = None,
    title: str | None = None,
    vault: Path | str | None = None,
    subdir: str = DEFAULT_SUBDIR,
    extras: dict[str, str] | None = None,
    cwd: Path | None = None,
    dry_run: bool = False,
    now: datetime | None = None,
) -> SessionSaveResult:
    """현재 세션 컨텍스트를 Obsidian vault에 저장.

    Args:
        note: 사용자가 명시한 메모 (스킬/CLI에서 전달).
        title: 노트 제목. 미지정 시 시간 + 브랜치 prefix로 자동 생성.
        vault: Obsidian vault 루트. 미지정 시 settings.yaml `obsidian_base` 또는
            `~/Documents/Obsidian Vault` 사용.
        subdir: vault 내 저장 디렉토리. 기본 `00_session`.
        extras: 추가로 본문에 포함할 섹션 (`{헤더: 내용}`).
        cwd: git 스냅샷을 수집할 디렉토리.
        dry_run: True면 파일을 쓰지 않고 본문만 반환.
        now: 테스트용 시각 주입.

    Returns:
        SessionSaveResult
    """
    cwd = cwd or Path.cwd()
    now = now or datetime.now()

    snap = collect_git_snapshot(cwd)
    project_name = cwd.resolve().name

    if not title:
        time_part = now.strftime("%H%M")
        branch_part = snap.branch or project_name
        title = f"{time_part} {branch_part}".strip()

    body = build_session_note(
        title=title,
        note=note,
        snapshot=snap,
        extras=extras,
        project_name=project_name,
        now=now,
    )

    vault_path = _resolve_vault(vault)
    target_dir = vault_path / subdir
    date_prefix = now.strftime("%Y-%m-%d")
    base_slug = slugify(title)
    base_name = f"{date_prefix}-{base_slug}"

    if dry_run:
        target_path = target_dir / f"{base_name}.md"
        return SessionSaveResult(path=target_path, title=title, body=body, created=False)

    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = _next_available_path(target_dir, base_name)
    target_path.write_text(body, encoding="utf-8")
    return SessionSaveResult(path=target_path, title=title, body=body, created=True)
