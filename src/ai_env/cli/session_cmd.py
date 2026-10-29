"""공용 Markdown 작업 기록 CLI 및 lifecycle hook 진입점."""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import cast

import click
import yaml

from ..core.session_archives import read_entry_text
from ..core.session_compaction import compact_entries
from ..core.session_hooks import handle_hook
from ..core.session_journal import (
    Agent,
    JournalEntry,
    Kind,
    Status,
    list_entries,
    save_entry,
)
from ..core.session_storage import Scope, project_directory
from . import console, main

_USER_ERRORS = (OSError, ValueError, EOFError, yaml.YAMLError)


@contextmanager
def _as_click_error() -> Iterator[None]:
    """경로·형식 오류를 traceback 없는 CLI 오류로 바꾼다."""
    try:
        yield
    except _USER_ERRORS as error:
        raise click.ClickException(str(error)) from error


@main.group("session")
@click.option(
    "--project",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path.cwd,
    help="기록할 프로젝트 cwd",
)
@click.option(
    "--root", type=click.Path(file_okay=False, path_type=Path), help="공용 기록 저장소 경로"
)
@click.pass_context
def session(ctx: click.Context, project: Path, root: Path | None) -> None:
    """Obsidian에 작업·리뷰·수정 기록을 남기고 찾는다."""
    ctx.obj = (project, root)


@session.command("record")
@click.option("--agent", type=click.Choice(["codex", "claude"]), required=True)
@click.option("--kind", type=click.Choice(["work", "review", "fix"]), default="work")
@click.option(
    "--scope", type=click.Choice(["kakao", "personal", "unclassified"]), default="unclassified"
)
@click.option("--title", default="", help="파일명에 포함할 짧은 주제 요약")
@click.option("--task", default="", help="Spec/Task 또는 공통 작업 식별자")
@click.option("--jira", default="", help="Jira Task 키 (미지정 시 브랜치에서 추출)")
@click.option(
    "--status",
    type=click.Choice(["recorded", "needs-review", "changes-requested", "approved", "blocked"]),
    default="recorded",
)
@click.option(
    "--body-file", type=click.Path(exists=True, dir_okay=False, path_type=Path), required=True
)
@click.option("--parent", default="", help="검토·수정 대상 기록의 절대경로")
@click.option("--session-id", default="manual")
@click.option("--dry-run", is_flag=True)
@click.pass_obj
def record(
    context: tuple[Path, Path | None],
    agent: str,
    kind: str,
    scope: str,
    title: str,
    task: str,
    jira: str,
    status: str,
    body_file: Path,
    parent: str,
    session_id: str,
    dry_run: bool,
) -> None:
    """작업·변경·검증·TODO를 담은 Markdown을 불변 기록으로 저장."""
    project, root = context
    with _as_click_error():
        entry = JournalEntry(
            cwd=str(project),
            agent=cast(Agent, agent),
            kind=cast(Kind, kind),
            scope=cast(Scope, scope),
            title=title,
            task=task,
            jira=jira,
            status=cast(Status, status),
            summary=body_file.read_text(encoding="utf-8"),
            parent=parent,
            session_id=session_id,
        )
        console.print_json(data=save_entry(entry, root, dry_run=dry_run))


@session.command("list")
@click.option("--agent", type=click.Choice(["codex", "claude"]))
@click.option("--kind", type=click.Choice(["work", "review", "fix", "checkpoint", "summary"]))
@click.option("--task", default=None)
@click.option("--limit", type=click.IntRange(1, 100), default=20)
@click.pass_obj
def list_records(
    context: tuple[Path, Path | None],
    agent: str | None,
    kind: str | None,
    task: str | None,
    limit: int,
) -> None:
    """프로젝트별 최근 기록과 읽을 Markdown 경로를 JSON 반환."""
    project, root = context
    with _as_click_error():
        console.print_json(
            data={
                "records": list_entries(
                    project, root, agent=agent, kind=kind, task=task, limit=limit
                )
            }
        )


@session.command("hook")
@click.option("--agent", type=click.Choice(["codex", "claude"]), required=True)
@click.pass_obj
def hook(context: tuple[Path, Path | None], agent: str) -> None:
    """stdin hook JSON을 처리하고 비차단 JSON만 반환."""
    try:
        payload = json.load(click.get_text_stream("stdin"))
        if not isinstance(payload, dict):
            raise ValueError("hook input must be an object")
        result = handle_hook(cast(Agent, agent), payload, context[1])
    except _USER_ERRORS:
        # payload나 예외에 포함된 민감한 원문은 출력하지 않는다.
        result = {
            "systemMessage": "공용 세션 기록 실패: 경로·권한·hook 입력을 확인하고 session record로 기록하세요."
        }
    console.print_json(data=result)


@session.command("compact")
@click.option("--session-id", default=None, help="지정한 세션만 즉시 요약")
@click.option("--agent", type=click.Choice(["codex", "claude"]), default="codex")
@click.option("--older-than-days", type=click.IntRange(0), default=7, show_default=True)
@click.option("--archive", is_flag=True, help="검증한 gzip 보관 후 Markdown을 짧은 안내로 교체")
@click.option("--dry-run", is_flag=True)
@click.pass_obj
def compact(
    context: tuple[Path, Path | None],
    session_id: str | None,
    agent: str,
    older_than_days: int,
    archive: bool,
    dry_run: bool,
) -> None:
    """원본 보존 상태로 세션별·오래된 날짜별 탐색 요약을 만든다."""
    with _as_click_error():
        results = compact_entries(
            context[0],
            context[1],
            session_id=session_id,
            agent=cast(Agent, agent),
            older_than_days=older_than_days,
            archive=archive,
            dry_run=dry_run,
        )
        console.print_json(data={"summaries": results})


@session.command("show")
@click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.pass_obj
def show(context: tuple[Path, Path | None], path: Path) -> None:
    """현재 프로젝트 기록을 gzip 보관 후에도 원문으로 출력한다."""
    with _as_click_error():
        if path.is_symlink() or path.resolve().parent != project_directory(context[0], context[1]):
            raise ValueError("Record outside current project")
        console.print(
            read_entry_text(path.resolve()), markup=False, highlight=False, soft_wrap=True
        )
