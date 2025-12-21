"""토픽 기반 3-Track 리서치 파이프라인

토픽 YAML을 읽고, 3개 Track(자동검색/Gemini/GPT)의 리서치를
오케스트레이션하는 핵심 로직.

사용법:
    topic = load_topic("bitcoin-automation", topics_dir)
    obsidian_path = get_obsidian_base_path(topic, vault_root)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

# ── 상수 ──

RESEARCH_DIRS = ("07_참고", "10_Research/Clippings")
"""리서치 파일을 탐색하는 Obsidian 하위 디렉토리 (레거시 + 워크플로우)"""

# ── Pydantic 모델 (토픽 YAML 스키마) ──


class TopicInfo(BaseModel):
    """토픽 기본 정보"""

    id: str
    name: str
    obsidian_base: str
    project_repo: str | None = None


class ResearchItem(BaseModel):
    """자동 검색 항목 (Track A)"""

    query: str
    output: str


class DeepResearchItem(BaseModel):
    """심층리서치 항목 (Track B/C)"""

    prompt: str
    output: str
    focus: str | None = None


class ResearchConfig(BaseModel):
    """3-Track 리서치 설정"""

    auto: list[ResearchItem] = Field(default_factory=list)
    gemini_deep: list[DeepResearchItem] = Field(default_factory=list)
    gpt_deep: list[DeepResearchItem] = Field(default_factory=list)


class PlanConfig(BaseModel):
    """Plan/Spec 생성 설정"""

    synthesis_prompt: str
    output: str


class CodeModule(BaseModel):
    """코드 모듈 정의"""

    name: str
    desc: str


class CodeConfig(BaseModel):
    """코드 생성 설정"""

    style: str = "tdd"
    target_repo: str | None = None
    test_framework: str = "pytest"
    modules: list[CodeModule] = Field(default_factory=list)


class WorkflowConfig(BaseModel):
    """워크플로우 확장 설정 (optional)"""

    obsidian_structure: str = "standard"  # standard | flat | custom
    enable_adr: bool = True
    enable_review: bool = True
    review_prompts: list[str] = Field(default_factory=list)


class TopicConfig(BaseModel):
    """토픽 YAML 전체 구조"""

    topic: TopicInfo
    research: ResearchConfig = Field(default_factory=ResearchConfig)
    plan: PlanConfig | None = None
    code: CodeConfig | None = None
    workflow: WorkflowConfig | None = None


# ── 핵심 함수 ──


def load_topic(topic_id: str, topics_dir: Path) -> TopicConfig:
    """토픽 YAML 파일 로드

    디렉토리 구조:
        config/topics/{topic_id}/topic.yaml  (신규 — 우선)
        config/topics/{topic_id}.yaml        (레거시 — fallback)

    Args:
        topic_id: 토픽 ID
        topics_dir: config/topics/ 디렉토리 경로

    Returns:
        파싱된 TopicConfig 객체

    Raises:
        FileNotFoundError: YAML 파일이 없을 때
        ValueError: YAML 파싱 실패 시
    """
    # 신규: topics/{id}/topic.yaml
    yaml_path = topics_dir / topic_id / "topic.yaml"
    # 레거시 fallback: topics/{id}.yaml
    if not yaml_path.exists():
        yaml_path = topics_dir / f"{topic_id}.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"토픽 파일을 찾을 수 없습니다: {yaml_path}")

    with open(yaml_path) as f:
        data = yaml.safe_load(f)

    if data is None:
        raise ValueError(f"빈 YAML 파일: {yaml_path}")

    return TopicConfig(**data)


def list_topics(topics_dir: Path) -> list[str]:
    """등록된 토픽 ID 목록 반환

    디렉토리 구조:
        config/topics/{topic_id}/topic.yaml  (신규)
        config/topics/{topic_id}.yaml        (레거시)

    Args:
        topics_dir: config/topics/ 디렉토리 경로

    Returns:
        토픽 ID 리스트
    """
    if not topics_dir.exists():
        return []

    ids: set[str] = set()
    # 신규: topics/{id}/topic.yaml
    for p in topics_dir.iterdir():
        if p.is_dir() and (p / "topic.yaml").exists():
            ids.add(p.name)
    # 레거시: topics/{id}.yaml
    for p in topics_dir.glob("*.yaml"):
        if p.stem != "README" and not p.stem.startswith("_"):
            ids.add(p.stem)

    return sorted(ids)


def _parse_prompt_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """마크다운 파일에서 YAML frontmatter와 본문 분리

    Args:
        text: 마크다운 파일 전체 텍스트

    Returns:
        (frontmatter dict, 본문 문자열) 튜플
    """
    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text

    fm_raw = parts[1].strip()
    body = parts[2].strip()

    fm = yaml.safe_load(fm_raw)
    if not isinstance(fm, dict):
        return {}, text

    return fm, body


def load_deep_research_prompts(
    topic_id: str,
    prompts_dir: Path,
) -> ResearchConfig | None:
    """토픽별 심층리서치 프롬프트 로드 (Markdown frontmatter 방식)

    프롬프트 탐색 경로 (우선순위):
        1. config/topics/{topic_id}/*.md (토픽 폴더 내 colocated)
        2. config/prompts/{topic_id}/*.md (레거시)

    frontmatter의 track(gemini/gpt), output, focus와 본문(prompt)을
    ResearchConfig로 반환한다.

    Args:
        topic_id: 토픽 ID
        prompts_dir: config/prompts/ 디렉토리 경로 (레거시 fallback)

    Returns:
        ResearchConfig (gemini_deep + gpt_deep 포함) 또는 없으면 None
    """
    # 신규: topics/{id}/ 폴더 내 .md 파일 (topic.yaml과 같은 위치)
    topic_dir = prompts_dir.parent / "topics" / topic_id
    if not topic_dir.is_dir():
        # 레거시: prompts/{id}/
        topic_dir = prompts_dir / topic_id
    if not topic_dir.is_dir():
        return None

    md_files = sorted(p for p in topic_dir.glob("*.md") if p.name != "README.md")
    if not md_files:
        return None

    gemini_items: list[DeepResearchItem] = []
    gpt_items: list[DeepResearchItem] = []

    for md_path in md_files:
        text = md_path.read_text(encoding="utf-8")
        fm, body = _parse_prompt_frontmatter(text)

        if not body or "track" not in fm or "output" not in fm:
            continue

        item = DeepResearchItem(
            prompt=body,
            output=str(fm["output"]),
            focus=fm.get("focus"),
        )

        track = str(fm["track"]).lower()
        if track == "gemini":
            gemini_items.append(item)
        elif track == "gpt":
            gpt_items.append(item)

    if not gemini_items and not gpt_items:
        return None

    return ResearchConfig(
        gemini_deep=gemini_items,
        gpt_deep=gpt_items,
    )


def get_obsidian_base_path(topic: TopicConfig, vault_root: Path) -> Path:
    """토픽의 Obsidian vault 기본 경로 계산

    Args:
        topic: 로드된 토픽 설정
        vault_root: Obsidian vault 루트 경로

    Returns:
        토픽의 Obsidian 기본 디렉토리 경로
    """
    return vault_root / topic.topic.obsidian_base


def generate_deep_research_prompt_file(
    items: list[DeepResearchItem],
    tool_name: str,
    output_path: Path,
    topic_name: str,
) -> Path:
    """심층리서치 프롬프트 파일 생성 (Gemini/GPT용)

    Args:
        items: DeepResearchItem 리스트
        tool_name: "Gemini" 또는 "GPT"
        output_path: 프롬프트 파일 저장 경로
        topic_name: 토픽 이름 (문서 제목용)

    Returns:
        생성된 파일 경로
    """
    today = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"# {tool_name} 심층리서치 프롬프트",
        "",
        f"토픽: **{topic_name}**",
        f"생성일: {today}",
        "",
        f"> 아래 프롬프트를 {tool_name} 웹 심층리서치에 복붙하세요.",
        "> 결과를 아래 지정된 파일명으로 Obsidian에 저장하세요.",
        "",
        "---",
        "",
    ]

    for i, item in enumerate(items, 1):
        lines.append(f"## 프롬프트 {i}")
        lines.append("")
        lines.append(f"**저장 경로**: `{item.output}`")
        if item.focus:
            lines.append(f"**조사 초점**: {item.focus}")
        lines.append("")
        lines.append("```")
        lines.append(item.prompt.strip())
        lines.append("```")
        lines.append("")
        lines.append("---")
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")

    return output_path


def generate_research_status(
    topic: TopicConfig,
    output_path: Path,
    existing_files: set[str] | None = None,
    manual_files: list[str] | None = None,
) -> Path:
    """리서치 진행 상황 체크리스트 생성

    Args:
        topic: 로드된 토픽 설정
        output_path: 상태 파일 저장 경로
        existing_files: 이미 존재하는 파일 경로 set (obsidian_base 기준 상대경로)
        manual_files: 수동 리서치 파일 경로 리스트

    Returns:
        생성된 파일 경로
    """
    if existing_files is None:
        existing_files = set()
    if manual_files is None:
        manual_files = []

    today = datetime.now().strftime("%Y-%m-%d")
    topic_id = topic.topic.id

    lines = [
        f"# 리서치 진행 상황: {topic.topic.name}",
        "",
        f"생성일: {today}",
        f"토픽 ID: `{topic_id}`",
        "",
    ]

    # Track A
    lines.append("## Track A: 자동검색 (Claude Code)")
    lines.append("")
    for item in topic.research.auto:
        check = "x" if item.output in existing_files else " "
        lines.append(f"- [{check}] `{item.output}`")
    lines.append("")

    # Track B
    lines.append("## Track B: Gemini 심층리서치 (API/수동)")
    lines.append("")
    for deep_item in topic.research.gemini_deep:
        check = "x" if deep_item.output in existing_files else " "
        focus_str = f" — {deep_item.focus}" if deep_item.focus else ""
        lines.append(f"- [{check}] `{deep_item.output}`{focus_str}")
    if not topic.research.gemini_deep:
        lines.append("- (없음)")
    lines.append("")
    lines.append("> 프롬프트: `_gemini-prompts.md` 참고")
    lines.append("")

    # Track C
    lines.append("## Track C: GPT 심층리서치 (API/수동)")
    lines.append("")
    for deep_item in topic.research.gpt_deep:
        check = "x" if deep_item.output in existing_files else " "
        focus_str = f" — {deep_item.focus}" if deep_item.focus else ""
        lines.append(f"- [{check}] `{deep_item.output}`{focus_str}")
    if not topic.research.gpt_deep:
        lines.append("- (없음)")
    lines.append("")
    lines.append("> 프롬프트: `_gpt-prompts.md` 참고")
    lines.append("")

    # Manual
    if manual_files:
        lines.append("## 수동 리서치")
        lines.append("")
        for mf in manual_files:
            lines.append(f"- [x] `{mf}`")
        lines.append("")

    # 다음 단계
    lines.append("---")
    lines.append("")
    lines.append("## 다음 단계")
    lines.append("")
    lines.append("Track B, C 완료 후 실행:")
    lines.append("```bash")
    lines.append(f'claude "/wf-spec {topic_id}"')
    lines.append("```")
    lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")

    return output_path


def collect_research_files(obsidian_base: Path) -> dict[str, list[Path]]:
    """Obsidian에 저장된 리서치 파일을 Track별로 분류

    두 폴더 체계(07_참고/, 10_Research/Clippings/)를 모두 탐색하며,
    기존 Track A/B/C 패턴에 맞지 않는 파일은 "manual" 트랙으로 분류한다.

    Args:
        obsidian_base: 토픽의 Obsidian 기본 경로

    Returns:
        {"track_a": [...], "track_b": [...], "track_c": [...], "manual": [...]}
    """
    result: dict[str, list[Path]] = {
        "track_a": [],
        "track_b": [],
        "track_c": [],
        "manual": [],
    }

    search_dirs = [obsidian_base / d for d in RESEARCH_DIRS]

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for f in sorted(search_dir.glob("*.md")):
            if f.name.startswith("_"):
                continue  # 프롬프트/상태 파일 제외
            if f.name.startswith("auto-"):
                result["track_a"].append(f)
            elif f.name.startswith("gemini"):
                result["track_b"].append(f)
            elif f.name.startswith("gpt"):
                result["track_c"].append(f)
            else:
                result["manual"].append(f)

    return result


def get_research_completion_status(
    topic: TopicConfig,
    obsidian_base: Path,
) -> dict[str, list[tuple[str, bool]]]:
    """각 Track의 리서치 파일 존재 여부를 반환

    YAML에 정의된 Track A/B/C 항목과 디스크에서 발견된 수동 리서치 파일을 모두 포함.

    Args:
        topic: 로드된 토픽 설정
        obsidian_base: 토픽의 Obsidian 기본 경로

    Returns:
        Track별 (output 경로, 존재 여부) 튜플 리스트
        {"track_a": [...], "track_b": [...], "track_c": [...], "manual": [...]}
    """
    result: dict[str, list[tuple[str, bool]]] = {
        "track_a": [],
        "track_b": [],
        "track_c": [],
        "manual": [],
    }

    for item in topic.research.auto:
        exists = (obsidian_base / item.output).exists()
        result["track_a"].append((item.output, exists))

    for deep_item in topic.research.gemini_deep:
        exists = (obsidian_base / deep_item.output).exists()
        result["track_b"].append((deep_item.output, exists))

    for deep_item in topic.research.gpt_deep:
        exists = (obsidian_base / deep_item.output).exists()
        result["track_c"].append((deep_item.output, exists))

    # 수동 리서치 파일 (패턴에 맞지 않는 .md 파일)
    collected = collect_research_files(obsidian_base)
    result["manual"] = [(str(f.relative_to(obsidian_base)), True) for f in collected["manual"]]

    return result


def validate_topic_for_phase(
    topic: TopicConfig,
    phase: str,
    obsidian_base: Path | None = None,
) -> tuple[bool, str]:
    """토픽이 해당 Phase를 실행할 수 있는 상태인지 검증

    Args:
        topic: 로드된 토픽 설정
        phase: "research", "synthesize", "code" 중 하나
        obsidian_base: Obsidian 기본 경로 (있으면 디스크 파일도 확인)

    Returns:
        (is_valid, message) 튜플
    """
    if phase == "research":
        if (
            not topic.research.auto
            and not topic.research.gemini_deep
            and not topic.research.gpt_deep
        ):
            return False, "research 섹션에 검색 항목이 없습니다"
        return True, "리서치 실행 가능"

    if phase == "synthesize":
        if not topic.plan:
            return False, "plan 섹션이 없습니다 (synthesis_prompt, output 필요)"

        has_yaml_research = bool(
            topic.research.auto or topic.research.gemini_deep or topic.research.gpt_deep
        )

        # 디스크에 실제 리서치 파일이 있는지 확인
        has_disk_research = False
        if obsidian_base is not None:
            files = collect_research_files(obsidian_base)
            total = sum(len(v) for v in files.values())
            has_disk_research = total > 0

        if not has_yaml_research and not has_disk_research:
            return False, "리서치 결과가 없습니다 (YAML 항목 또는 파일 모두 없음)"
        return True, "종합 실행 가능"

    if phase == "code":
        if not topic.code:
            return False, "code 섹션이 없습니다"
        if not topic.code.modules:
            return False, "code.modules가 비어있습니다"
        if not topic.plan:
            return False, "plan 섹션이 없습니다 (spec 기반 코딩에 필요)"
        return True, "코드 생성 가능"

    return False, f"알 수 없는 phase: {phase}"


def generate_auto_search_markdown(
    query: str,
    results: list[dict[str, str]],
    output_path: Path,
) -> Path:
    """자동 검색 결과를 마크다운으로 저장

    Args:
        query: 검색 쿼리
        results: [{"title": ..., "url": ..., "snippet": ...}, ...]
        output_path: 저장 경로

    Returns:
        생성된 파일 경로
    """
    today = datetime.now().strftime("%Y-%m-%d")

    lines = [
        "---",
        "source: auto-search",
        f'query: "{query}"',
        f"date: {today}",
        "track: A (Claude Code 자동검색)",
        "---",
        "",
        f"# {query}",
        "",
    ]

    for i, r in enumerate(results, 1):
        title = r.get("title", "Untitled")
        url = r.get("url", "")
        snippet = r.get("snippet", "")

        lines.append(f"## {i}. {title}")
        if url:
            lines.append(f"- URL: {url}")
        lines.append("")
        if snippet:
            lines.append(snippet)
            lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")

    return output_path
