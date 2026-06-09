"""Obsidian vault에 현재 세션 컨텍스트를 마크다운 노트로 저장.

스킬/대화 도중 호출되어 현재 세션의 핵심 컨텍스트(사용자 노트, git 스냅샷)를
Obsidian PARA vault의 지정 디렉토리에 영구 저장한다.

CLI(`ai-env session save`) 및 `.claude/skills/session-save` 스킬에서 사용한다.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .config import expand_path, load_settings

DEFAULT_VAULT = "~/Documents/Obsidian Vault"
DEFAULT_SUBDIR = "00_session"
DEFAULT_CONTEXT_MAX_CHARS = 12000
MAX_SLUG_SUFFIX_TRIES = 100

_SLUG_CLEAN = re.compile(r"[^a-zA-Z0-9가-힣\-_]+")
_SLUG_DASHES = re.compile(r"-{2,}")
_PATH_LIKE = re.compile(
    r"(?:(?:\.{1,2}|~|/)[\w가-힣@%+=:,./\-]+|[\w가-힣_.\-]+/[\w가-힣@%+=:,./\-]+)"
)
_ERROR_LIKE = re.compile(
    r"(error|failed|failure|exception|traceback|실패|에러|오류)", re.IGNORECASE
)


@dataclass
class SessionSaveResult:
    """세션 저장 결과."""

    path: Path
    title: str
    body: str
    created: bool = True


@dataclass
class SessionLatestResult:
    """최신 세션 조회 결과."""

    path: Path | None
    body: str
    project_name: str
    found: bool


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


def _shorten(text: str, max_len: int = 700) -> str:
    """한 줄 요약용으로 공백을 접고 길이를 제한."""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _append_unique(values: list[str], value: str, *, limit: int) -> None:
    """순서를 보존하며 중복 없이 최대 limit개만 유지."""
    value = value.strip()
    if not value or value in values:
        return
    values.append(value)
    if len(values) > limit:
        del values[0 : len(values) - limit]


def _extract_paths(text: str) -> list[str]:
    """대화 텍스트에서 파일/디렉토리처럼 보이는 토큰 추출."""
    paths: list[str] = []
    for match in _PATH_LIKE.findall(text):
        cleaned = match.strip("`'\"()[]{}<>.,")
        if "/" in cleaned and len(cleaned) <= 180:
            _append_unique(paths, cleaned, limit=40)
    return paths


def _content_text(content: object) -> tuple[str, list[str]]:
    """Claude/Codex JSONL content에서 사람이 읽을 텍스트와 tool 신호 추출."""
    texts: list[str] = []
    tools: list[str] = []

    if isinstance(content, str):
        return content, tools

    if isinstance(content, list):
        for item in content:
            if isinstance(item, str):
                texts.append(item)
                continue
            if not isinstance(item, dict):
                continue
            item_type = str(item.get("type", ""))
            if item_type == "text":
                texts.append(str(item.get("text", "")))
            elif item_type == "tool_use":
                name = str(item.get("name", "tool"))
                tool_input = item.get("input", {})
                if isinstance(tool_input, dict):
                    command = tool_input.get("cmd") or tool_input.get("command")
                    target = tool_input.get("path") or tool_input.get("file_path")
                    suffix = command or target or ""
                    tools.append(_shorten(f"{name}: {suffix}", 220))
                else:
                    tools.append(_shorten(f"{name}: {tool_input}", 220))
            elif item_type == "tool_result" and item.get("is_error"):
                texts.append(_shorten(str(item.get("content", "")), 500))
        return "\n".join(part for part in texts if part), tools

    if isinstance(content, dict):
        if "text" in content:
            texts.append(str(content.get("text", "")))
        if "content" in content:
            nested_text, nested_tools = _content_text(content.get("content"))
            texts.append(nested_text)
            tools.extend(nested_tools)
        return "\n".join(part for part in texts if part), tools

    return "", tools


def _extract_transcript_event(obj: dict[str, object]) -> tuple[str, str, list[str]]:
    """JSONL 한 줄에서 role, text, tool 신호를 추출."""
    role = str(obj.get("role") or obj.get("type") or "")
    content: object = obj.get("content", "")

    message = obj.get("message")
    if isinstance(message, dict):
        role = str(message.get("role") or role)
        content = message.get("content", content)

    if not content and "text" in obj:
        content = obj.get("text", "")

    text, tools = _content_text(content)
    return role.lower(), text, tools


def compress_transcript(
    transcript_path: Path | str | None,
    *,
    max_chars: int = DEFAULT_CONTEXT_MAX_CHARS,
) -> str:
    """Claude/Codex transcript JSONL을 후속 세션용 마크다운으로 압축.

    외부 LLM을 호출하지 않고 규칙 기반으로 사용자 요청, 진행/결정, 도구 사용,
    파일 경로, 오류 신호, 최근 타임라인을 추출한다.
    """
    if transcript_path is None:
        return ""

    path = expand_path(str(transcript_path))
    if not path.exists() or not path.is_file():
        return ""

    user_messages: list[str] = []
    assistant_notes: list[str] = []
    tool_events: list[str] = []
    paths: list[str] = []
    errors: list[str] = []
    timeline: list[str] = []
    parsed = 0

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""

    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue

        role, text, tools = _extract_transcript_event(obj)
        if not text and not tools:
            continue
        parsed += 1

        for tool in tools:
            _append_unique(tool_events, tool, limit=30)

        short_text = _shorten(text, 900)
        for found_path in _extract_paths(text):
            _append_unique(paths, found_path, limit=40)
        if _ERROR_LIKE.search(text):
            _append_unique(errors, short_text, limit=12)

        if role in {"user", "human"}:
            _append_unique(user_messages, short_text, limit=16)
            timeline.append(f"- user: {_shorten(text, 260)}")
        elif role == "assistant":
            if short_text:
                _append_unique(assistant_notes, short_text, limit=18)
                timeline.append(f"- assistant: {_shorten(text, 260)}")
        elif tools:
            timeline.append(f"- tools: {', '.join(tools[:3])}")

    if not parsed:
        return ""

    parts: list[str] = [
        f"- source: `{path}`",
        f"- parsed_events: {parsed}",
        "",
    ]

    if user_messages:
        parts.extend(["### User Requests", ""])
        parts.extend(f"- {item}" for item in user_messages)
        parts.append("")

    if assistant_notes:
        parts.extend(["### Progress / Decisions", ""])
        parts.extend(f"- {item}" for item in assistant_notes)
        parts.append("")

    if tool_events:
        parts.extend(["### Tool Signals", ""])
        parts.extend(f"- {item}" for item in tool_events)
        parts.append("")

    if paths:
        parts.extend(["### Files / Paths", ""])
        parts.extend(f"- `{item}`" for item in paths)
        parts.append("")

    if errors:
        parts.extend(["### Errors / Risks", ""])
        parts.extend(f"- {item}" for item in errors)
        parts.append("")

    if timeline:
        parts.extend(["### Recent Timeline", ""])
        parts.extend(timeline[-24:])
        parts.append("")

    body = "\n".join(parts).rstrip()
    if len(body) <= max_chars:
        return body
    return body[: max_chars - 1].rstrip() + "…"


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


def _project_session_slug(
    *,
    project_name: str,
    title: str,
    session_id: str | None,
    agent: str | None,
) -> str:
    """세션 파일명용 프로젝트 prefix slug 생성."""
    project_slug = slugify(project_name, max_len=40)
    if session_id:
        suffix = f"session-{session_id[:8]}"
    elif agent:
        suffix = f"session-{agent}"
    else:
        suffix = slugify(title, max_len=60)

    suffix_slug = slugify(suffix, max_len=60)
    if suffix_slug.startswith(project_slug):
        return suffix_slug
    return slugify(f"{project_slug}-{suffix_slug}", max_len=90)


def build_session_note(
    *,
    title: str,
    note: str | None,
    snapshot: GitSnapshot,
    extras: dict[str, str] | None = None,
    project_name: str | None = None,
    cwd: Path | None = None,
    session_id: str | None = None,
    agent: str | None = None,
    transcript_path: Path | str | None = None,
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
            "cwd": str(cwd) if cwd else "",
            "session_id": session_id or "",
            "agent": agent or "",
            "transcript_path": str(transcript_path) if transcript_path else "",
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
    transcript_path: Path | str | None = None,
    session_id: str | None = None,
    agent: str | None = None,
    dry_run: bool = False,
    now: datetime | None = None,
) -> SessionSaveResult:
    """현재 세션 컨텍스트를 Obsidian vault에 저장.

    Args:
        note: 사용자가 명시한 메모 (스킬/CLI에서 전달).
        title: 노트 제목. 미지정 시 프로젝트 + 세션 prefix로 자동 생성.
        vault: Obsidian vault 루트. 미지정 시 settings.yaml `obsidian_base` 또는
            `~/Documents/Obsidian Vault` 사용.
        subdir: vault 내 저장 디렉토리. 기본 `00_session`.
        extras: 추가로 본문에 포함할 섹션 (`{헤더: 내용}`).
        cwd: git 스냅샷을 수집할 디렉토리.
        transcript_path: Claude/Codex transcript JSONL 경로. 있으면 압축 요약 포함.
        session_id: 에이전트 세션 ID. 파일명/프론트매터에 기록.
        agent: claude/codex 등 에이전트 이름.
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
        title = f"{project_name} session"
        if session_id:
            title = f"{title} {session_id[:8]}"
        elif snap.branch:
            title = f"{title} {snap.branch}"

    merged_extras: dict[str, str] = {}
    transcript_summary = compress_transcript(transcript_path)
    if transcript_summary:
        merged_extras["Compressed Conversation"] = transcript_summary
    if extras:
        merged_extras.update(extras)

    body = build_session_note(
        title=title,
        note=note,
        snapshot=snap,
        extras=merged_extras or None,
        project_name=project_name,
        cwd=cwd.resolve(),
        session_id=session_id,
        agent=agent,
        transcript_path=transcript_path,
        now=now,
    )

    vault_path = _resolve_vault(vault)
    target_dir = vault_path / subdir
    date_hour_prefix = now.strftime("%Y-%m-%d %H")
    base_slug = _project_session_slug(
        project_name=project_name,
        title=title,
        session_id=session_id,
        agent=agent,
    )
    base_name = f"{date_hour_prefix} {base_slug}"

    if dry_run:
        target_path = target_dir / f"{base_name}.md"
        return SessionSaveResult(path=target_path, title=title, body=body, created=False)

    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = _next_available_path(target_dir, base_name)
    target_path.write_text(body, encoding="utf-8")
    return SessionSaveResult(path=target_path, title=title, body=body, created=True)


def _parse_frontmatter(body: str) -> dict[str, str]:
    """간단한 YAML frontmatter에서 scalar 값만 추출."""
    lines = body.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    values: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    return values


def find_latest_session(
    *,
    vault: Path | str | None = None,
    subdir: str = DEFAULT_SUBDIR,
    cwd: Path | None = None,
    project_name: str | None = None,
) -> SessionLatestResult:
    """프로젝트별 최신 Obsidian 세션 노트 조회."""
    cwd = cwd or Path.cwd()
    project_name = project_name or cwd.resolve().name
    vault_path = _resolve_vault(vault)
    target_dir = vault_path / subdir
    if not target_dir.exists():
        return SessionLatestResult(None, "", project_name, False)

    project_slug = slugify(project_name, max_len=40)
    candidates: list[Path] = []
    for path in target_dir.glob("*.md"):
        try:
            head = path.read_text(encoding="utf-8", errors="replace")[:4096]
        except OSError:
            continue
        fm = _parse_frontmatter(head)
        if fm.get("project") == project_name or project_slug in slugify(path.stem, max_len=180):
            candidates.append(path)

    if not candidates:
        return SessionLatestResult(None, "", project_name, False)

    latest = max(candidates, key=lambda item: item.stat().st_mtime)
    body = latest.read_text(encoding="utf-8", errors="replace")
    return SessionLatestResult(latest, body, project_name, True)


def build_latest_session_context(
    *,
    vault: Path | str | None = None,
    subdir: str = DEFAULT_SUBDIR,
    cwd: Path | None = None,
    project_name: str | None = None,
    max_chars: int = DEFAULT_CONTEXT_MAX_CHARS,
) -> SessionLatestResult:
    """에이전트 시작 시 주입하기 좋은 최신 세션 컨텍스트 생성."""
    result = find_latest_session(
        vault=vault,
        subdir=subdir,
        cwd=cwd,
        project_name=project_name,
    )
    if not result.found or result.path is None:
        return result

    header = [
        f"# Latest Session Context: {result.project_name}",
        f"- path: {result.path}",
        "",
    ]
    body = result.body.strip()
    rendered = "\n".join(header) + body
    if len(rendered) > max_chars:
        rendered = rendered[: max_chars - 1].rstrip() + "…"
    return SessionLatestResult(result.path, rendered + "\n", result.project_name, True)
