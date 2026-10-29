"""원본을 보존하며 세션·날짜별 탐색 요약을 만든다. LLM은 호출하지 않는다."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from .session_archives import archive_entry, read_entry_text
from .session_journal import Agent, JournalEntry, list_entries, save_entry
from .session_storage import KST, digest, journal_lock, project_directory, split_record

EXCERPT_CHARACTERS = 400
Row = dict[str, object]


def _created(row: Row) -> datetime:
    return datetime.fromisoformat(str(row["created"]))


def _group_rows(
    rows: list[Row], session_id: str | None, agent: Agent, cutoff: date
) -> dict[str, list[Row]]:
    """세션 지정 시 해당 도구·세션, 미지정 시 기준일 이전 날짜별로 묶는다."""
    groups: dict[str, list[Row]] = defaultdict(list)
    for row in sorted(rows, key=_created):
        if session_id is not None:
            if row["session_id"] == session_id and row["agent"] == agent:
                groups[f"세션-{agent}-{session_id}"].append(row)
            continue
        day = _created(row).astimezone(KST).date()
        if day < cutoff:
            groups[f"일별-{day}"].append(row)
    return groups


def _pending_groups(
    project: Path, root: Path | None, session_id: str | None, agent: Agent, cutoff: date
) -> list[tuple[str, list[Row], list[Row], Row | None]]:
    """그룹별 (요약 제목, 전체 기록, 직전 요약 이후 기록, 직전 요약)을 반환한다."""
    rows = list_entries(project, root, limit=100000)
    latest_summary: dict[str, Row] = {}
    for row in rows:  # 최신순이므로 제목별 첫 요약이 가장 최근 요약이다.
        if row["kind"] == "summary":
            latest_summary.setdefault(str(row["title"]), row)
    sources = [row for row in rows if row["kind"] != "summary"]
    groups = []
    for group, members in _group_rows(sources, session_id, agent, cutoff).items():
        title = f"{group}-요약"
        previous = latest_summary.get(title)
        pending = [row for row in members if not previous or _created(row) > _created(previous)]
        groups.append((title, members, pending, previous))
    return groups


def _summary_text(rows: list[Row]) -> str:
    lines = [
        "## 작업 흐름",
        "",
        "> 자동 요약은 메타데이터와 보고 앞부분의 발췌다. 의미 기반 압축·검증 판정은 수행하지 않는다. 원문 링크에서 전체 검증·TODO를 확인한다.",
        "",
    ]
    for row in rows:
        path = Path(str(row["path"]))
        _, body = split_record(read_entry_text(path))
        report = body.split("## 작업·검증·TODO 보고\n\n", 1)[-1].split("\n\n## 연결 기록", 1)[0]
        lines.append(
            f"### {row['title']}\n\n- 도구/유형/상태: {row['agent']} / {row['kind']} / {row.get('report_status', row['status'])}\n- Task/Jira/브랜치: {row['task']} / {row.get('jira', '')} / {row['branch']}\n- 원문: [[{path.stem}]]\n\n{report[:EXCERPT_CHARACTERS]}{' … [원문 계속]' if len(report) > EXCERPT_CHARACTERS else ''}\n"
        )
    return "\n".join(lines)


def compact_entries(
    project: Path,
    root: Path | None = None,
    *,
    session_id: str | None = None,
    agent: Agent = "codex",
    older_than_days: int = 7,
    archive: bool = False,
    dry_run: bool = False,
) -> list[dict[str, str]]:
    """세션 종료 요약 또는 오래된 날짜별 요약을 멱등하게 만든다.

    같은 제목의 요약이 있으면 그 이후 기록만 새로 묶는다. 일별 요약은 도구와
    무관하게 날짜당 하나이며, 요약이 끝난 날짜는 원문을 다시 읽지 않는다.

    Args:
        project: 현재 프로젝트. 다른 프로젝트는 조회하지 않는다.
        root: 선택적 공용 저장소.
        session_id: 지정하면 해당 도구·세션만 즉시 묶는다.
        agent: 세션 필터 및 요약을 작성한 도구.
        older_than_days: 세션 미지정 시 이 기간보다 오래된 날짜만 묶는다.
        archive: 검증한 gzip 원문 보관 후 기존 Markdown을 짧은 안내로 교체한다.
        dry_run: 요약 파일을 만들지 않는다.

    Returns:
        요약 기록별 저장 결과. 원본은 삭제하거나 수정하지 않는다.

    Raises:
        ValueError: 음수 기간을 지정한 경우.
    """
    if older_than_days < 0:
        raise ValueError("older_than_days must be nonnegative")
    directory = project_directory(project, root)
    if not directory.is_dir():
        return []
    cutoff = datetime.now(KST).date() - timedelta(days=older_than_days)
    # 두 도구의 SessionEnd가 겹쳐도 요약 조회부터 저장까지 한 번만 실행한다.
    with journal_lock(directory, ".compact.lock"):
        groups = _pending_groups(project, root, session_id, agent, cutoff)
        results = []
        for title, members, pending, previous in groups:
            if previous and not pending:
                results.append({"status": "unchanged", "path": str(previous["path"])})
            else:
                results.append(
                    save_entry(
                        JournalEntry(
                            cwd=str(project),
                            agent=agent,
                            kind="summary",
                            title=title,
                            session_id=session_id or "daily-compaction",
                            turn_id=digest("\n".join(str(row["id"]) for row in pending)),
                            summary=_summary_text(pending),
                        ),
                        root,
                        dry_run=dry_run,
                    )
                )
            if archive and not dry_run:
                for row in members:
                    if not row.get("archived"):
                        archive_entry(Path(str(row["path"])))
    return results
