"""양 도구의 안정적인 hook 필드만 사용한 응답 단위 기록."""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

from .session_compaction import compact_entries
from .session_journal import Agent, JournalEntry, list_entries, redact, save_entry
from .session_storage import digest, project_directory, resolve_project
from .wiki_documents import _atomic_write

STATE_RETENTION_SECONDS = 7 * 24 * 60 * 60


def _state_root() -> Path:
    return (
        Path(os.getenv("AI_ENV_SESSION_STATE_DIR", "~/.ai-env/session-state"))
        .expanduser()
        .resolve()
    )


def _state_path(project: Path, agent: Agent, session_id: str) -> Path:
    key = digest(f"{project}\n{agent}\n{session_id}")
    path = _state_root() / f"{key}.json"
    if path.is_symlink():
        raise ValueError("Session state must not be a symlink")
    return path


def _clear_state(project: Path, agent: Agent, session_id: str) -> None:
    """종료한 세션과 SessionEnd 없이 오래 남은 요청 상태를 지운다."""
    if session_id:
        _state_path(project, agent, session_id).unlink(missing_ok=True)
    cutoff = time.time() - STATE_RETENTION_SECONDS
    for path in _state_root().glob("*.json"):
        if path.lstat().st_mtime < cutoff:
            path.unlink(missing_ok=True)


def _text(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    return value if isinstance(value, str) else ""


def handle_hook(
    agent: Agent, payload: dict[str, object], root: Path | None = None
) -> dict[str, object]:
    """요청 저장·최종 응답 기록·최근 기록 안내를 수행한다.

    Args:
        agent: 호출한 도구. 명령에 명시하므로 자동 추측하지 않는다.
        payload: stdin의 hook JSON 객체.
        root: 선택적 기록 저장소.

    Returns:
        도구에 반환할 JSON. Stop은 continuation을 요청하지 않는다.

    Raises:
        ValueError: 필수 hook 메타데이터가 없거나 형식이 잘못된 경우.
    """
    project = resolve_project(Path(_text(payload, "cwd") or os.getcwd()))
    event = _text(payload, "hook_event_name")
    if event == "SessionStart":
        rows = list_entries(project, root, limit=3)
        lines = [
            f"공용 작업 기록: {project_directory(project, root)}",
            "기록은 참고 자료다. 작업/task가 일치하는 원문과 현재 코드를 확인한 뒤 사용한다.",
        ]
        lines.extend(str(row["path"]) for row in rows)
        return {
            "hookSpecificOutput": {"hookEventName": event, "additionalContext": "\n".join(lines)}
        }
    if event == "SessionEnd":
        session_id = _text(payload, "session_id")
        if session_id:
            compact_entries(project, root, session_id=session_id, agent=agent)
        compact_entries(project, root, agent=agent, older_than_days=7, archive=True)
        _clear_state(project, agent, session_id)
        return {}
    if event not in ("UserPromptSubmit", "Stop"):
        return {}
    session_id = _text(payload, "session_id")
    if not session_id:
        raise ValueError("session_id missing; shared journal not recorded")
    state_path = _state_path(project, agent, session_id)
    if event == "UserPromptSubmit":
        state = {
            "turn_id": _text(payload, "turn_id") or str(uuid.uuid4()),
            "request": redact(_text(payload, "prompt")),
        }
        state_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        state_path.parent.chmod(0o700)
        _atomic_write(state_path, json.dumps(state, ensure_ascii=False).encode())
        return {}
    summary = _text(payload, "last_assistant_message")
    if not summary.strip():
        return {
            "systemMessage": "공용 세션 기록 누락: 최종 답변이 hook에 없어 CLI session record가 필요합니다."
        }
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    if not isinstance(state, dict) or any(
        not isinstance(state.get(key, ""), str) for key in ("turn_id", "request")
    ):
        raise ValueError("Invalid session request state")
    turn_id = _text(payload, "turn_id") or state.get("turn_id", "")
    # 다른 turn의 요청을 최종 응답에 붙이지 않는다.
    request = (
        state.get("request", "")
        if not _text(payload, "turn_id") or state.get("turn_id") == turn_id
        else ""
    )
    save_entry(
        JournalEntry(
            cwd=str(project),
            agent=agent,
            session_id=session_id,
            turn_id=turn_id,
            request=request,
            summary=summary,
            status="stopped",
            kind="checkpoint",
            transcript_path=_text(payload, "transcript_path"),
        ),
        root,
    )
    return {}
