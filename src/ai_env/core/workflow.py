"""6-Phase 워크플로우 자동화

Obsidian 워크스페이스 스캐폴딩, 템플릿 렌더링, 워크플로우 상태 관리.

사용법:
    from ai_env.core.workflow import scaffold_obsidian_workspace
    result = scaffold_obsidian_workspace(topic, vault_root, templates_dir)
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .pipeline import RESEARCH_DIRS, TopicConfig

# ── 폴더 구조 정의 ──

WORKSPACE_DIRS = [
    "10_Research/Clippings",
    "10_Research/Briefs",
    "20_Specs/ADR",
    "30_Tasks",
    "40_Reviews",
    "50_Logs",
]

# Phase 이름 매핑
PHASE_NAMES = {
    "intake": "Phase 1: Intake",
    "research": "Phase 2: Research",
    "spec": "Phase 3: Spec Freeze",
    "implementing": "Phase 4: Implement",
    "review": "Phase 5: Review",
    "done": "Phase 6: Close",
}


# ── 템플릿 렌더링 ──


def render_template(template_path: Path, variables: dict[str, str]) -> str:
    """{{변수}} 치환하여 템플릿 렌더링

    Args:
        template_path: 템플릿 파일 경로
        variables: {변수명: 값} 딕셔너리

    Returns:
        치환된 문자열
    """
    content = template_path.read_text(encoding="utf-8")

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return variables.get(key, match.group(0))

    return re.sub(r"\{\{(\w+)\}\}", _replace, content)


# ── 스캐폴딩 ──


def scaffold_obsidian_workspace(
    topic: TopicConfig,
    vault_root: Path,
    templates_dir: Path,
) -> dict[str, Path]:
    """토픽용 Obsidian 워크스페이스 생성

    Args:
        topic: 로드된 토픽 설정
        vault_root: Obsidian vault 루트 경로
        templates_dir: config/templates/ 디렉토리 경로

    Returns:
        {파일종류: 경로} dict (생성된 파일들)
    """
    obsidian_base = vault_root / topic.topic.obsidian_base
    today = datetime.now().strftime("%Y-%m-%d")
    topic_id = topic.topic.id

    variables = {
        "topic_id": topic_id,
        "topic_name": topic.topic.name,
        "task_id": topic_id,
        "project_name": topic.topic.name,
        "date": today,
        "title": "",
        "adr_number": "001",
    }

    result: dict[str, Path] = {}

    # 1. 폴더 구조 생성
    for dir_path in WORKSPACE_DIRS:
        (obsidian_base / dir_path).mkdir(parents=True, exist_ok=True)

    # 2. TASK 파일 생성
    task_template = templates_dir / "obsidian" / "TASK.md"
    if task_template.exists():
        task_path = obsidian_base / "30_Tasks" / f"TASK-{topic_id}.md"
        if not task_path.exists():
            task_content = render_template(task_template, variables)
            task_path.write_text(task_content, encoding="utf-8")
        result["task"] = task_path

    # 3. SPEC 템플릿 배치
    spec_template = templates_dir / "obsidian" / "SPEC.md"
    if spec_template.exists():
        spec_path = obsidian_base / "20_Specs" / f"SPEC-{topic_id}.md"
        if not spec_path.exists():
            spec_content = render_template(spec_template, variables)
            spec_path.write_text(spec_content, encoding="utf-8")
        result["spec"] = spec_path

    return result


def generate_phase_prompts(
    topic: TopicConfig,
    vault_root: Path,
    templates_dir: Path,
) -> list[Path]:
    """토픽별 Phase 프롬프트 파일 생성

    토픽의 research questions, spec path 등을
    프롬프트 템플릿에 채워서 Obsidian _prompts/ 폴더에 저장.

    Args:
        topic: 로드된 토픽 설정
        vault_root: Obsidian vault 루트 경로
        templates_dir: config/templates/ 디렉토리 경로

    Returns:
        생성된 프롬프트 파일 경로 리스트
    """
    obsidian_base = vault_root / topic.topic.obsidian_base
    prompts_dir = obsidian_base / "_prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    topic_id = topic.topic.id
    generated: list[Path] = []

    # 공통 변수
    base_vars = {
        "topic_id": topic_id,
        "topic_name": topic.topic.name,
        "date": today,
        "task_file": f"30_Tasks/TASK-{topic_id}.md",
        "spec_output": f"20_Specs/SPEC-{topic_id}.md",
        "spec_file": f"20_Specs/SPEC-{topic_id}.md",
        "spec_template": f"20_Specs/SPEC-{topic_id}.md",
        "brief_output": f"10_Research/Briefs/BRIEF-{topic_id}.md",
        "brief_file": f"10_Research/Briefs/BRIEF-{topic_id}.md",
        "clippings_dir": "10_Research/Clippings/",
        "adr_dir": "20_Specs/ADR/",
        "review_output": f"40_Reviews/REV-{topic_id}.md",
        "target_repo": topic.code.target_repo if topic.code and topic.code.target_repo else ".",
    }

    # Gemini 수집 프롬프트에 research items 추가
    gemini_vars = {**base_vars}
    if topic.research.gemini_deep:
        prompt_blocks = []
        for i, item in enumerate(topic.research.gemini_deep, 1):
            block = f"## 프롬프트 {i}\n\n"
            block += f"**저장 경로**: `10_Research/Clippings/{item.output}`\n"
            if item.focus:
                block += f"**조사 초점**: {item.focus}\n"
            block += f"\n```\n{item.prompt.strip()}\n```\n"
            prompt_blocks.append(block)
        gemini_vars["research_prompts"] = "\n---\n\n".join(prompt_blocks)
    else:
        gemini_vars["research_prompts"] = "(Gemini 리서치 항목 없음)"

    # 각 프롬프트 템플릿 렌더링
    prompt_templates = [
        ("gemini-collect.md", gemini_vars),
        ("claude-brief.md", base_vars),
        ("claude-spec-adr.md", base_vars),
        ("claude-review.md", base_vars),
    ]

    for template_name, variables in prompt_templates:
        template_path = templates_dir / "prompts" / template_name
        if template_path.exists():
            output_path = prompts_dir / template_name
            content = render_template(template_path, variables)
            output_path.write_text(content, encoding="utf-8")
            generated.append(output_path)

    return generated


# ── 워크플로우 상태 ──


def get_workflow_status(
    topic: TopicConfig,
    obsidian_base: Path,
) -> dict[str, str | None]:
    """워크플로우 진행 상태 반환

    Args:
        topic: 로드된 토픽 설정
        obsidian_base: 토픽의 Obsidian 기본 경로

    Returns:
        {
            "phase": "intake|research|spec|implementing|review|done",
            "task_file": path or None,
            "spec_file": path or None,
            "brief_file": path or None,
            "review_file": path or None,
            "research_pct": "3/5" or None,
        }
    """
    topic_id = topic.topic.id
    result: dict[str, str | None] = {
        "phase": "intake",
        "task_file": None,
        "spec_file": None,
        "brief_file": None,
        "review_file": None,
        "research_pct": None,
    }

    # 파일 존재 확인
    task_path = obsidian_base / "30_Tasks" / f"TASK-{topic_id}.md"
    spec_path = obsidian_base / "20_Specs" / f"SPEC-{topic_id}.md"
    brief_path = obsidian_base / "10_Research" / "Briefs" / f"BRIEF-{topic_id}.md"
    review_path = obsidian_base / "40_Reviews" / f"REV-{topic_id}.md"

    if task_path.exists():
        result["task_file"] = str(task_path)
    if spec_path.exists():
        result["spec_file"] = str(spec_path)
    if brief_path.exists():
        result["brief_file"] = str(brief_path)
    if review_path.exists():
        result["review_file"] = str(review_path)

    # 리서치 진행률 계산 — 두 폴더 체계 모두 확인
    # (워크플로우: 10_Research/Clippings/, 레거시: 07_참고/)
    total_expected = (
        len(topic.research.auto) + len(topic.research.gemini_deep) + len(topic.research.gpt_deep)
    )
    research_found = 0
    for search_dir in [obsidian_base / d for d in RESEARCH_DIRS]:
        if search_dir.exists():
            research_found += sum(1 for f in search_dir.glob("*.md") if not f.name.startswith("_"))

    if total_expected > 0:
        result["research_pct"] = f"{research_found}/{total_expected}"
    elif research_found > 0:
        # YAML에 research 항목이 없지만 수동 리서치 파일 존재
        result["research_pct"] = f"{research_found}/{research_found} (manual)"

    # Phase 판단 로직
    if result["review_file"]:
        result["phase"] = "done"
    elif result["spec_file"] and _spec_has_content(spec_path):
        if topic.code and topic.code.modules:
            result["phase"] = "implementing"
        else:
            result["phase"] = "spec"
    elif result["brief_file"]:
        result["phase"] = "spec"
    elif research_found > 0:
        result["phase"] = "research"
    elif result["task_file"]:
        result["phase"] = "intake"

    return result


def generate_workflow_status_file(
    topic: TopicConfig,
    obsidian_base: Path,
    output_path: Path,
) -> Path:
    """워크플로우 상태 체크리스트 파일 생성

    Args:
        topic: 로드된 토픽 설정
        obsidian_base: 토픽의 Obsidian 기본 경로
        output_path: 상태 파일 저장 경로

    Returns:
        생성된 파일 경로
    """
    status = get_workflow_status(topic, obsidian_base)
    today = datetime.now().strftime("%Y-%m-%d")
    topic_id = topic.topic.id

    current_phase = status["phase"] or "intake"

    # Phase 순서
    phases = ["intake", "research", "spec", "implementing", "review", "done"]
    current_idx = phases.index(current_phase) if current_phase in phases else 0

    lines = [
        f"# 워크플로우 상태: {topic.topic.name}",
        "",
        f"갱신일: {today}",
        f"토픽 ID: `{topic_id}`",
        f"현재 Phase: **{PHASE_NAMES.get(current_phase, current_phase)}**",
        "",
        "## Phase Checklist",
        "",
    ]

    for i, phase in enumerate(phases):
        if i < current_idx:
            check = "x"
        elif i == current_idx:
            check = "~"  # 진행중
        else:
            check = " "
        lines.append(f"- [{check}] {PHASE_NAMES.get(phase, phase)}")

    lines.append("")

    # 파일 상태
    lines.append("## 산출물")
    lines.append("")
    file_items = [
        ("TASK", status.get("task_file")),
        ("Brief", status.get("brief_file")),
        ("SPEC", status.get("spec_file")),
        ("Review", status.get("review_file")),
    ]
    for label, path in file_items:
        mark = "✅" if path else "⬜"
        lines.append(f"- {mark} {label}")

    if status.get("research_pct"):
        lines.append(f"- 📊 리서치: {status['research_pct']}")

    lines.append("")

    # 다음 단계 안내
    lines.append("## 다음 단계")
    lines.append("")
    if current_phase == "intake":
        lines.append(f'```bash\nclaude "/wf-research {topic_id}"\n```')
    elif current_phase == "research":
        lines.append(f'```bash\nclaude "/wf-spec {topic_id}"\n```')
    elif current_phase == "spec":
        lines.append(f'```bash\nclaude "/wf-code {topic_id}"\n```')
    elif current_phase == "implementing":
        lines.append(f'```bash\nclaude "/wf-review {topic_id}"\n```')
    elif current_phase == "review":
        lines.append("리뷰 결과 확인 후 Follow-up 처리")
    else:
        lines.append("✅ 워크플로우 완료!")

    lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")

    return output_path


def _spec_has_content(spec_path: Path) -> bool:
    """SPEC 파일에 템플릿 이상의 실제 내용이 있는지 확인

    Note: 호출 전에 spec_path.exists()가 보장되어야 한다.
    """
    if not spec_path.exists():
        return False
    content = spec_path.read_text(encoding="utf-8")
    # 템플릿 기본값(~300자) 이상의 실제 내용이 있는지 체크
    return len(content) > 500 and "한 문단 요약" not in content
