"""양 도구의 안정적인 hook 필드만 사용한 응답 단위 기록."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import cast

import yaml

from .session_compaction import compact_entries
from .session_journal import Agent, JournalEntry, list_entries, redact, save_entry
from .session_storage import digest, project_directory, resolve_project
from .wiki_documents import _atomic_write

STATE_RETENTION_SECONDS = 7 * 24 * 60 * 60
# SessionStart 안내: 후속 기록이 없는 아래 상태를 처리 대기로 먼저 보여준다.
PENDING_STATUSES = ("needs-review", "changes-requested", "blocked")
START_PENDING_LIMIT = 5
START_RECENT_LIMIT = 3
HOOK_USER_ERRORS = (OSError, ValueError, EOFError, yaml.YAMLError)
HOOK_FAILURE = {
    "systemMessage": "공용 세션 기록 실패: 경로·권한·hook 입력을 확인하고 session record로 기록하세요."
}
# 사용자 지시가 아닌 도구 주입 프롬프트. 백그라운드 작업 알림·Codex 추천 안전검사.
SYSTEM_PROMPT_PREFIXES = (
    "<task-notification>",
    "You are an expert at upholding safety and compliance standards for Codex",
)


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


def _start_line(row: dict[str, object]) -> str:
    task = f" {row['task']}" if row.get("task") else ""
    return (
        f"- [{row['report_status']}] {row['kind']}/{row['agent']}{task}: "
        f"{row['title']} — {row['path']}"
    )


def _session_start(project: Path, root: Path | None) -> dict[str, object]:
    """다음에 처리할 리뷰 요청을 먼저, 그다음 최근 완료 보고를 안내한다.

    checkpoint·summary는 대화 흔적이라 제외한다. 다른 기록의 parent가 된 요청은
    후속 리뷰·수정이 이미 있으므로 처리 대기에서 뺀다.
    """
    rows = [
        row
        for row in list_entries(project, root, limit=200)
        if row["kind"] in ("work", "review", "fix")
    ]
    answered = {str(row.get("parent") or "") for row in rows}
    pending = [
        row
        for row in rows
        if row["report_status"] in PENDING_STATUSES
        and f"[[{Path(str(row['path'])).stem}]]" not in answered
    ][:START_PENDING_LIMIT]
    recent = [row for row in rows if row not in pending][:START_RECENT_LIMIT]
    lines = [
        f"공용 작업 기록: {project_directory(project, root)}",
        "기록은 참고 자료다. 작업/task가 일치하는 원문과 현재 코드를 확인한 뒤 사용한다.",
    ]
    if pending:
        lines.append("처리 대기 (리뷰 요청·수정 요청·막힘):")
        lines.extend(_start_line(row) for row in pending)
    if recent:
        lines.append("최근 완료 보고:")
        lines.extend(_start_line(row) for row in recent)
    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\n".join(lines),
        }
    }


def _session_end(project: Path, agent: Agent, session_id: str, root: Path | None) -> None:
    if session_id:
        compact_entries(project, root, session_id=session_id, agent=agent)
    compact_entries(project, root, agent=agent, older_than_days=7, archive=True)
    _clear_state(project, agent, session_id)


def _read_state(state_path: Path) -> dict[str, str]:
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    if not isinstance(state, dict) or any(
        not isinstance(state.get(key, ""), str) for key in ("turn_id", "request", "system")
    ):
        raise ValueError("Invalid session request state")
    return state


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
    session_id = _text(payload, "session_id")
    if event == "SessionStart":
        return _session_start(project, root)
    if event == "SessionEnd":
        _session_end(project, agent, session_id, root)
        return {}
    if event not in ("UserPromptSubmit", "Stop"):
        return {}
    if not session_id:
        raise ValueError("session_id missing; shared journal not recorded")
    state_path = _state_path(project, agent, session_id)
    if event == "UserPromptSubmit":
        prompt = _text(payload, "prompt")
        state = {
            "turn_id": _text(payload, "turn_id") or str(uuid.uuid4()),
            "request": redact(prompt),
            "system": "yes" if prompt.lstrip().startswith(SYSTEM_PROMPT_PREFIXES) else "",
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
    state = _read_state(state_path)
    turn_id = _text(payload, "turn_id") or state.get("turn_id", "")
    if state.get("system") and state.get("turn_id") == turn_id:
        return {}
    save_entry(
        JournalEntry(
            cwd=str(project),
            agent=agent,
            session_id=session_id,
            turn_id=turn_id,
            # 다른 turn의 요청을 최종 응답에 붙이지 않는다.
            request=state.get("request", "") if state.get("turn_id") == turn_id else "",
            summary=summary,
            status="stopped",
            kind="checkpoint",
            transcript_path=_text(payload, "transcript_path"),
        ),
        root,
    )
    return {}


def hook_response(agent: Agent, raw: str, root: Path | None = None) -> dict[str, object]:
    """stdin hook JSON 문자열을 처리하고 도구에 돌려줄 JSON을 만든다.

    Args:
        agent: 호출한 도구.
        raw: hook stdin 원문.
        root: 선택적 기록 저장소.

    Returns:
        hook 결과. 사용자 입력·경로 오류는 원문 없이 systemMessage로만 알린다.
    """
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("hook input must be an object")
        return handle_hook(agent, payload, root)
    except HOOK_USER_ERRORS:
        # payload나 예외에 포함된 민감한 원문은 출력하지 않는다.
        return dict(HOOK_FAILURE)


def main(argv: list[str] | None = None) -> int:
    """hook 스크립트 진입점. CLI 전체를 import하지 않아 매 턴 지연을 줄인다.

    Args:
        argv: 명령행 인자. 기본은 sys.argv.

    Returns:
        항상 0. 기록 실패가 도구 실행을 막지 않게 한다.
    """
    parser = argparse.ArgumentParser(prog="python -m ai_env.core.session_hooks")
    parser.add_argument("--agent", choices=("codex", "claude"), required=True)
    agent = cast(Agent, parser.parse_args(argv).agent)
    print(json.dumps(hook_response(agent, sys.stdin.read()), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
