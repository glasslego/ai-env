"""파이프라인 CLI 명령어

ai-env pipeline 서브커맨드:
  - list: 등록된 토픽 목록
  - info: 토픽 상세 정보
  - research: Phase 1 리서치 실행
  - dispatch: Track B/C 심층리서치 API 디스패치
  - status: 리서치 진행 상황
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from ..core.config import get_project_root
from ..core.pipeline import (
    DeepResearchItem,
    ResearchConfig,
    TopicConfig,
    generate_deep_research_prompt_file,
    generate_research_status,
    get_obsidian_base_path,
    get_research_completion_status,
    list_topics,
    load_deep_research_prompts,
    load_topic,
    validate_topic_for_phase,
)
from ..core.workflow import (
    PHASE_NAMES,
    generate_phase_prompts,
    generate_workflow_status_file,
    get_workflow_status,
    scaffold_obsidian_workspace,
)

console = Console()

VAULT_ROOT = Path.home() / "Documents" / "Obsidian Vault"


def _print_deep_research_track(
    track_label: str,
    items: list[DeepResearchItem],
    tool_name: str,
    ref_dir: Path,
    topic_name: str,
) -> None:
    """심층리서치 트랙(B/C)의 프롬프트 생성 결과를 출력하는 공통 헬퍼"""
    console.print(f"\n[bold]{track_label}[/bold]")
    if items:
        prompt_path = generate_deep_research_prompt_file(
            items=items,
            tool_name=tool_name,
            output_path=ref_dir / f"_{tool_name.lower()}-prompts.md",
            topic_name=topic_name,
        )
        console.print(f"  [green]✓[/green] 프롬프트 파일 생성: {prompt_path}")
        for deep_item in items:
            focus = f" ({deep_item.focus})" if deep_item.focus else ""
            console.print(f"  • {deep_item.output}{focus}")
    else:
        console.print("  [dim](없음)[/dim]")


def _get_topics_dir() -> Path:
    return get_project_root() / "config" / "topics"


def _load_topic_or_fail(topic_id: str) -> TopicConfig:
    """토픽 로드, 실패 시 에러 메시지 출력 후 종료"""
    try:
        return load_topic(topic_id, _get_topics_dir())
    except FileNotFoundError:
        console.print(f"[red]✗ 토픽을 찾을 수 없습니다: {topic_id}[/red]")
        available = list_topics(_get_topics_dir())
        if available:
            console.print(f"  등록된 토픽: {', '.join(available)}")
        raise SystemExit(1) from None


# ── CLI 그룹 등록 ──

from . import main  # noqa: E402


@main.group()
def pipeline() -> None:
    """토픽 기반 3-Track 리서치 파이프라인"""
    pass


# ── list ──
@pipeline.command("list")
def pipeline_list() -> None:
    """등록된 토픽 목록"""
    topics_dir = _get_topics_dir()
    topic_ids = list_topics(topics_dir)

    if not topic_ids:
        console.print("[yellow]등록된 토픽이 없습니다.[/yellow]")
        console.print(f"  토픽 YAML 추가: {topics_dir}/")
        return

    table = Table(title="등록된 토픽")
    table.add_column("ID", style="cyan")
    table.add_column("이름", style="green")
    table.add_column("Obsidian 경로")
    table.add_column("코드", justify="center")

    for tid in topic_ids:
        try:
            t = load_topic(tid, topics_dir)
            code_status = "✅" if t.code else "—"
            table.add_row(tid, t.topic.name, t.topic.obsidian_base, code_status)
        except Exception as e:
            table.add_row(tid, f"[red]로드 실패: {e}[/red]", "", "")

    console.print(table)


# ── info ──
@pipeline.command("info")
@click.argument("topic_id")
def pipeline_info(topic_id: str) -> None:
    """토픽 상세 정보"""
    topic = _load_topic_or_fail(topic_id)

    console.print(f"\n[bold cyan]📋 {topic.topic.name}[/bold cyan]")
    console.print(f"  ID: {topic.topic.id}")
    console.print(f"  Obsidian: {topic.topic.obsidian_base}")
    if topic.topic.project_repo:
        console.print(f"  Repo: {topic.topic.project_repo}")

    # Research tracks
    console.print("\n[bold]리서치 트랙[/bold]")
    console.print(f"  Track A (자동): {len(topic.research.auto)}건")
    console.print(f"  Track B (Gemini): {len(topic.research.gemini_deep)}건")
    console.print(f"  Track C (GPT): {len(topic.research.gpt_deep)}건")

    # Plan
    if topic.plan:
        console.print("\n[bold]Plan/Spec[/bold]")
        console.print(f"  출력: {topic.plan.output}")

    # Code
    if topic.code:
        console.print("\n[bold]코드 생성[/bold]")
        console.print(f"  스타일: {topic.code.style}")
        console.print(f"  프레임워크: {topic.code.test_framework}")
        console.print(f"  모듈: {len(topic.code.modules)}개")
        for m in topic.code.modules:
            console.print(f"    - {m.name}: {m.desc}")


# ── research ──
@pipeline.command("research")
@click.argument("topic_id")
@click.option("--vault", default=str(VAULT_ROOT), help="Obsidian vault 루트 경로")
def pipeline_research(topic_id: str, vault: str) -> None:
    """Phase 1: 3-Track 리서치 실행 (자동검색 + 프롬프트 생성)"""
    topic = _load_topic_or_fail(topic_id)

    is_valid, msg = validate_topic_for_phase(topic, "research")
    if not is_valid:
        console.print(f"[red]✗ {msg}[/red]")
        raise SystemExit(1) from None

    vault_root = Path(vault)
    obsidian_base = get_obsidian_base_path(topic, vault_root)
    ref_dir = obsidian_base / "07_참고"
    ref_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"\n[bold cyan]🔍 리서치 파이프라인: {topic.topic.name}[/bold cyan]\n")

    # Track A: 자동 검색 쿼리 목록 표시
    console.print("[bold]Track A: 자동 웹검색 (Agent-Teams 병렬)[/bold]")
    if topic.research.auto:
        console.print(f"  검색 쿼리 {len(topic.research.auto)}건 (병렬 실행):")
        for item in topic.research.auto:
            console.print(f"  • [cyan]{item.query}[/cyan]")
            console.print(f"    → {item.output}")
        console.print("\n  [dim]💡 슬래시 커맨드에서 Task 도구로 병렬 자동 실행됩니다[/dim]")
    else:
        console.print("  [dim](없음)[/dim]")

    # Track B/C: 심층리서치 프롬프트 파일 생성
    _print_deep_research_track(
        "Track B: Gemini 심층리서치",
        topic.research.gemini_deep,
        "Gemini",
        ref_dir,
        topic.topic.name,
    )
    _print_deep_research_track(
        "Track C: GPT 심층리서치", topic.research.gpt_deep, "GPT", ref_dir, topic.topic.name
    )

    # 상태 체크리스트 생성
    status_path = generate_research_status(
        topic=topic,
        output_path=ref_dir / "_research-status.md",
        existing_files=set(),
    )
    console.print(f"\n[green]✓[/green] 상태 파일 생성: {status_path}")

    # 다음 단계 안내
    console.print("\n[bold cyan]📋 다음 단계:[/bold cyan]")
    console.print(f'  1. Track A 자동검색: [cyan]claude "/wf-research {topic_id}"[/cyan]')
    console.print("  2. Gemini 웹에서 심층리서치 실행 → 결과를 Obsidian에 저장")
    console.print("  3. GPT 웹에서 심층리서치 실행 → 결과를 Obsidian에 저장")
    console.print(f"  4. 상태 확인: [cyan]ai-env pipeline status {topic_id}[/cyan]")
    console.print(f'  5. 종합: [cyan]claude "/wf-spec {topic_id}"[/cyan]')


# ── dispatch ──
@pipeline.command("dispatch")
@click.argument("topic_id")
@click.option("--vault", default=str(VAULT_ROOT), help="Obsidian vault 루트 경로")
@click.option(
    "--track",
    type=click.Choice(["all", "gemini", "gpt"]),
    default="all",
    help="디스패치할 트랙 선택",
)
@click.option("--timeout", default=1200, help="API 타임아웃 (초)")
def pipeline_dispatch(topic_id: str, vault: str, track: str, timeout: int) -> None:
    """Track B/C 심층리서치 API 디스패치

    Gemini Deep Research API와 OpenAI Deep Research API를 호출하여
    심층리서치를 자동 실행하고 결과를 Obsidian에 저장한다.
    API 키가 없는 트랙은 프롬프트 파일 생성으로 fallback.
    """
    from ..core.research import dispatch_deep_research

    topic = _load_topic_or_fail(topic_id)
    vault_root = Path(vault)
    obsidian_base = get_obsidian_base_path(topic, vault_root)
    ref_dir = obsidian_base / "07_참고"
    ref_dir.mkdir(parents=True, exist_ok=True)

    # 프롬프트 매핑 파일 우선 참조 (config/prompts/deep-research.yaml)
    prompts_dir = get_project_root() / "config" / "prompts"
    prompts_override = load_deep_research_prompts(topic_id, prompts_dir)
    if prompts_override:
        research = prompts_override
        prompt_source = f"config/topics/{topic_id}/*.md"
    else:
        research = topic.research
        prompt_source = f"config/topics/{topic_id}/topic.yaml"

    console.print(f"\n[bold cyan]🔬 심층리서치 디스패치: {topic.topic.name}[/bold cyan]")
    console.print(f"  [dim]프롬프트 소스: {prompt_source}[/dim]\n")

    # API 키 로드
    google_key, openai_key = _resolve_api_keys(track)

    # 디스패치 대상 확인
    gemini_items = research.gemini_deep if google_key else []
    gpt_items = research.gpt_deep if openai_key else []

    if not gemini_items and not gpt_items:
        console.print("[yellow]⚠ 디스패치할 항목이 없습니다.[/yellow]")
        if not google_key and research.gemini_deep:
            console.print("  [dim]GOOGLE_API_KEY가 .env에 없어 Track B 스킵[/dim]")
        if not openai_key and research.gpt_deep:
            console.print("  [dim]OPENAI_API_KEY가 .env에 없어 Track C 스킵[/dim]")

        # Fallback: 프롬프트 파일 생성
        _fallback_prompt_files(research, topic.topic.name, ref_dir)
        return

    # 디스패치 대상 표시
    if gemini_items:
        console.print(f"[bold]Track B: Gemini Deep Research[/bold] ({len(gemini_items)}건)")
        for item in gemini_items:
            focus = f" ({item.focus})" if item.focus else ""
            console.print(f"  • {item.output}{focus}")

    if gpt_items:
        console.print(f"[bold]Track C: GPT Deep Research[/bold] ({len(gpt_items)}건)")
        for item in gpt_items:
            focus = f" ({item.focus})" if item.focus else ""
            console.print(f"  • {item.output}{focus}")

    console.print(f"\n[dim]⏳ API 호출 중... (타임아웃: {timeout}초)[/dim]\n")

    # 비동기 디스패치 실행
    results = asyncio.run(
        dispatch_deep_research(
            topic=topic,
            obsidian_base=obsidian_base,
            google_api_key=google_key,
            openai_api_key=openai_key,
            timeout=timeout,
            research_override=research if prompts_override is not None else None,
        )
    )

    # 결과 표시
    _display_dispatch_results(results)

    # API 키 없는 트랙 fallback
    if (not google_key and research.gemini_deep) or (not openai_key and research.gpt_deep):
        fallback_research = ResearchConfig(
            gemini_deep=research.gemini_deep if not google_key else [],
            gpt_deep=research.gpt_deep if not openai_key else [],
        )
        _fallback_prompt_files(fallback_research, topic.topic.name, ref_dir)

    # 다음 단계
    console.print("\n[bold cyan]📋 다음 단계:[/bold cyan]")
    console.print(f"  상태 확인: [cyan]ai-env pipeline status {topic_id}[/cyan]")
    console.print(f'  종합: [cyan]claude "/wf-spec {topic_id}"[/cyan]')


def _resolve_api_keys(
    track: str,
) -> tuple[str | None, str | None]:
    """트랙 선택에 따라 API 키를 로드하고 빈 문자열을 None으로 정규화"""
    from ..core.secrets import get_secrets_manager

    secrets = get_secrets_manager()
    google_key = secrets.get("GOOGLE_API_KEY") if track in ("all", "gemini") else None
    openai_key = secrets.get("OPENAI_API_KEY") if track in ("all", "gpt") else None

    # 빈 문자열 → None
    if google_key is not None and not google_key:
        google_key = None
    if openai_key is not None and not openai_key:
        openai_key = None

    return google_key, openai_key


def _display_dispatch_results(results: list[Any]) -> None:
    """디스패치 결과를 요약 출력"""
    success_count = 0
    fail_count = 0

    for r in results:
        provider_label = "Gemini" if r.provider == "gemini" else "GPT"
        if r.content:
            success_count += 1
            console.print(
                f"  [green]✓[/green] {provider_label}: {r.output_path} ({r.elapsed_seconds:.0f}초)"
            )
        else:
            fail_count += 1
            console.print(f"  [red]✗[/red] {provider_label}: {r.output_path} — {r.error}")

    console.print(f"\n  완료: [green]{success_count}[/green] 성공, ", end="")
    console.print(f"[red]{fail_count}[/red] 실패")


def _fallback_prompt_files(research: ResearchConfig, topic_name: str, ref_dir: Path) -> None:
    """API 키 없을 때 프롬프트 파일 생성 fallback"""
    console.print("\n[dim]프롬프트 파일을 생성합니다 (웹에서 수동 실행):[/dim]")

    if research.gemini_deep:
        gemini_path = generate_deep_research_prompt_file(
            items=research.gemini_deep,
            tool_name="Gemini",
            output_path=ref_dir / "_gemini-prompts.md",
            topic_name=topic_name,
        )
        console.print(f"  [green]✓[/green] Gemini 프롬프트: {gemini_path}")

    if research.gpt_deep:
        gpt_path = generate_deep_research_prompt_file(
            items=research.gpt_deep,
            tool_name="GPT",
            output_path=ref_dir / "_gpt-prompts.md",
            topic_name=topic_name,
        )
        console.print(f"  [green]✓[/green] GPT 프롬프트: {gpt_path}")

    console.print(
        "\n  [dim]💡 .env에 GOOGLE_API_KEY/OPENAI_API_KEY를 추가하면 API 자동 호출됩니다[/dim]"
    )


# ── status ──
@pipeline.command("status")
@click.argument("topic_id")
@click.option("--vault", default=str(VAULT_ROOT), help="Obsidian vault 루트 경로")
def pipeline_status(topic_id: str, vault: str) -> None:
    """리서치 진행 상황 확인"""
    topic = _load_topic_or_fail(topic_id)
    vault_root = Path(vault)
    obsidian_base = get_obsidian_base_path(topic, vault_root)

    console.print(f"\n[bold cyan]📊 리서치 상태: {topic.topic.name}[/bold cyan]\n")

    # 예상 파일 vs 실제 파일 비교
    completion = get_research_completion_status(topic, obsidian_base)

    # Track별 상태 표시
    table = Table()
    table.add_column("Track", style="cyan")
    table.add_column("진행", justify="center")
    table.add_column("파일별 상태")

    for track_name, track_label, hide_empty in [
        ("track_a", "A: 자동검색", False),
        ("track_b", "B: Gemini", False),
        ("track_c", "C: GPT", False),
        ("manual", "수동 리서치", True),
    ]:
        items = completion[track_name]
        if not items:
            if hide_empty:
                continue  # 수동 트랙은 파일 없으면 표시하지 않음
            table.add_row(track_label, "—", "[dim]없음[/dim]")
            continue

        done = sum(1 for _, exists in items if exists)
        total = len(items)
        progress = f"{done}/{total}"

        file_status_parts = []
        for output_path, exists in items:
            name = Path(output_path).name
            mark = "[green]✅[/green]" if exists else "[red]❌[/red]"
            file_status_parts.append(f"{mark} {name}")
        file_status = ", ".join(file_status_parts)

        table.add_row(track_label, progress, file_status)

    console.print(table)

    # 전체 완료율
    total_expected = sum(len(v) for v in completion.values())
    total_found = sum(1 for items in completion.values() for _, exists in items if exists)

    if total_expected > 0:
        pct = total_found / total_expected * 100
        console.print(f"\n  진행률: {total_found}/{total_expected} ({pct:.0f}%)")

    # Plan/Spec 존재 여부
    if topic.plan:
        spec_path = obsidian_base / topic.plan.output
        if spec_path.exists():
            console.print(f"\n  [green]✓[/green] Plan/Spec: {topic.plan.output}")
        else:
            console.print(f"\n  [dim]○[/dim] Plan/Spec: {topic.plan.output} (미생성)")

    # 다음 단계
    if total_found >= total_expected and total_found > 0:
        console.print("\n  [green]✓ 모든 리서치 완료! 다음 단계:[/green]")
        console.print(f'    [cyan]claude "/wf-spec {topic_id}"[/cyan]')
    elif total_found > 0:
        console.print("\n  [yellow]○ 일부 완료. 누락된 파일을 확인하세요.[/yellow]")
    else:
        console.print("\n  [red]✗ 아직 리서치 결과가 없습니다.[/red]")
        console.print(f'    먼저: [cyan]claude "/wf-research {topic_id}"[/cyan]')
        console.print("    또는 수동 리서치 파일을 07_참고/ 디렉토리에 배치하세요.")


# ── scaffold ──
@pipeline.command("scaffold")
@click.argument("topic_id")
@click.option("--vault", default=str(VAULT_ROOT), help="Obsidian vault 루트 경로")
def pipeline_scaffold(topic_id: str, vault: str) -> None:
    """토픽용 Obsidian 워크스페이스 + 프롬프트 생성"""
    topic = _load_topic_or_fail(topic_id)
    vault_root = Path(vault)
    templates_dir = get_project_root() / "config" / "templates"

    console.print(f"\n[bold cyan]🏗️  워크스페이스 스캐폴딩: {topic.topic.name}[/bold cyan]\n")

    # 1. 폴더 구조 + TASK/SPEC 생성
    created = scaffold_obsidian_workspace(topic, vault_root, templates_dir)
    for file_type, file_path in created.items():
        console.print(f"  [green]✓[/green] {file_type}: {file_path}")

    # 2. Phase별 프롬프트 파일 생성
    obsidian_base = get_obsidian_base_path(topic, vault_root)
    prompts = generate_phase_prompts(topic, vault_root, templates_dir)
    if prompts:
        console.print(f"\n  [green]✓[/green] 프롬프트 {len(prompts)}개 생성:")
        for p in prompts:
            console.print(f"    - {p.name}")

    # 3. 워크플로우 상태 파일 생성
    status_path = generate_workflow_status_file(
        topic=topic,
        obsidian_base=obsidian_base,
        output_path=obsidian_base / "_workflow-status.md",
    )
    console.print(f"  [green]✓[/green] 상태 파일: {status_path}")

    # 다음 단계 안내
    console.print("\n[bold cyan]📋 다음 단계:[/bold cyan]")
    console.print("  1. TASK 파일 편집: Research Questions 작성")
    console.print(f'  2. 리서치 시작: [cyan]claude "/wf-research {topic_id}"[/cyan]')
    console.print(f'  3. 또는 전체 초기화: [cyan]claude "/wf-init {topic_id}"[/cyan]')


# ── workflow (상태 확인) ──
@pipeline.command("workflow")
@click.argument("topic_id")
@click.option("--vault", default=str(VAULT_ROOT), help="Obsidian vault 루트 경로")
def pipeline_workflow(topic_id: str, vault: str) -> None:
    """워크플로우 진행 상태 확인"""
    topic = _load_topic_or_fail(topic_id)
    vault_root = Path(vault)
    obsidian_base = get_obsidian_base_path(topic, vault_root)

    status = get_workflow_status(topic, obsidian_base)
    current_phase = status.get("phase") or "intake"

    # 상태 파일 자동 재생성 (워크스페이스가 존재하는 경우)
    status_file = obsidian_base / "_workflow-status.md"
    if status_file.exists() or (obsidian_base / "30_Tasks").exists():
        generate_workflow_status_file(topic, obsidian_base, status_file)

    console.print(f"\n[bold cyan]📊 워크플로우: {topic.topic.name}[/bold cyan]\n")
    console.print(f"  현재 Phase: [bold]{PHASE_NAMES.get(current_phase, current_phase)}[/bold]")

    # 산출물 상태
    console.print("\n[bold]산출물[/bold]")
    file_items = [
        ("TASK", status.get("task_file")),
        ("Brief", status.get("brief_file")),
        ("SPEC", status.get("spec_file")),
        ("Review", status.get("review_file")),
    ]
    for label, path in file_items:
        if path:
            console.print(f"  [green]✓[/green] {label}: {Path(path).name}")
        else:
            console.print(f"  [dim]○[/dim] {label}: (미생성)")

    if status.get("research_pct"):
        console.print(f"  📊 리서치: {status['research_pct']}")

    # 다음 단계
    console.print("\n[bold]다음 단계[/bold]")
    if current_phase == "intake":
        console.print(f'  [cyan]claude "/wf-research {topic_id}"[/cyan]')
    elif current_phase == "research":
        console.print(f'  [cyan]claude "/wf-spec {topic_id}"[/cyan]')
    elif current_phase == "spec":
        console.print(f'  [cyan]claude "/wf-code {topic_id}"[/cyan]')
    elif current_phase == "implementing":
        console.print(f'  [cyan]claude "/wf-review {topic_id}"[/cyan]')
    elif current_phase == "review":
        console.print("  리뷰 결과 확인 후 Follow-up 처리")
    else:
        console.print("  [green]✅ 워크플로우 완료![/green]")
