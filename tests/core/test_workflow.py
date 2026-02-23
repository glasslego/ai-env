"""워크플로우 모듈 테스트

scaffold_obsidian_workspace, render_template, generate_phase_prompts,
get_workflow_status 등 핵심 함수 테스트.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from ai_env.core.pipeline import (
    CodeConfig,
    CodeModule,
    DeepResearchItem,
    PlanConfig,
    ResearchConfig,
    ResearchItem,
    TopicConfig,
    TopicInfo,
    WorkflowConfig,
)
from ai_env.core.workflow import (
    PHASE_NAMES,
    WORKSPACE_DIRS,
    generate_phase_prompts,
    generate_workflow_status_file,
    get_workflow_status,
    render_template,
    scaffold_obsidian_workspace,
)


@pytest.fixture()
def sample_topic() -> TopicConfig:
    """테스트용 토픽 설정"""
    return TopicConfig(
        topic=TopicInfo(
            id="test-topic",
            name="테스트 토픽",
            obsidian_base="99_Test/test-topic",
        ),
        research=ResearchConfig(
            auto=[
                ResearchItem(query="test query 1", output="07_참고/auto-test1.md"),
                ResearchItem(query="test query 2", output="07_참고/auto-test2.md"),
            ],
            gemini_deep=[
                DeepResearchItem(
                    prompt="Gemini 리서치 프롬프트",
                    output="gemini-test.md",
                    focus="핵심 분석",
                ),
            ],
            gpt_deep=[
                DeepResearchItem(
                    prompt="GPT 리서치 프롬프트",
                    output="gpt-test.md",
                ),
            ],
        ),
        plan=PlanConfig(
            synthesis_prompt="종합 분석 프롬프트",
            output="SPEC-test-topic.md",
        ),
        code=CodeConfig(
            style="tdd",
            target_repo="/tmp/test-repo",
            test_framework="pytest",
            modules=[
                CodeModule(name="core", desc="핵심 모듈"),
            ],
        ),
    )


@pytest.fixture()
def vault_root(tmp_path: Path) -> Path:
    """임시 Obsidian vault 루트"""
    return tmp_path / "vault"


@pytest.fixture()
def templates_dir(tmp_path: Path) -> Path:
    """임시 템플릿 디렉토리 (실제 템플릿 복사)"""
    import shutil

    src = Path(__file__).parents[2] / "config" / "templates"
    dst = tmp_path / "templates"
    if src.exists():
        shutil.copytree(src, dst)
    else:
        # 테스트용 최소 템플릿 생성
        (dst / "obsidian").mkdir(parents=True)
        (dst / "prompts").mkdir(parents=True)
        (dst / "obsidian" / "TASK.md").write_text(
            "# TASK: {{topic_name}}\ntopic_id: {{topic_id}}\ndate: {{date}}"
        )
        (dst / "obsidian" / "SPEC.md").write_text("# SPEC: {{project_name}}\ndate: {{date}}")
        (dst / "prompts" / "claude-brief.md").write_text("# Brief\ntopic: {{topic_name}}")
    return dst


# ── render_template 테스트 ──


class TestRenderTemplate:
    """render_template 함수 테스트"""

    def test_basic_substitution(self, tmp_path: Path) -> None:
        """기본 변수 치환"""
        template = tmp_path / "test.md"
        template.write_text("Hello {{name}}, today is {{date}}")

        result = render_template(template, {"name": "World", "date": "2026-01-01"})
        assert result == "Hello World, today is 2026-01-01"

    def test_missing_variable_kept(self, tmp_path: Path) -> None:
        """누락 변수는 원본 유지"""
        template = tmp_path / "test.md"
        template.write_text("{{known}} and {{unknown}}")

        result = render_template(template, {"known": "value"})
        assert result == "value and {{unknown}}"

    def test_empty_variables(self, tmp_path: Path) -> None:
        """빈 변수 딕셔너리"""
        template = tmp_path / "test.md"
        template.write_text("No {{vars}} here")

        result = render_template(template, {})
        assert result == "No {{vars}} here"

    def test_multiple_same_variable(self, tmp_path: Path) -> None:
        """같은 변수 여러번 치환"""
        template = tmp_path / "test.md"
        template.write_text("{{x}} + {{x}} = {{x}}{{x}}")

        result = render_template(template, {"x": "1"})
        assert result == "1 + 1 = 11"


# ── scaffold_obsidian_workspace 테스트 ──


class TestScaffoldObsidianWorkspace:
    """scaffold_obsidian_workspace 함수 테스트"""

    def test_creates_folders(
        self,
        sample_topic: TopicConfig,
        vault_root: Path,
        templates_dir: Path,
    ) -> None:
        """폴더 구조 생성"""
        scaffold_obsidian_workspace(sample_topic, vault_root, templates_dir)

        base = vault_root / sample_topic.topic.obsidian_base
        for dir_path in WORKSPACE_DIRS:
            assert (base / dir_path).is_dir(), f"{dir_path} 폴더가 없습니다"

    def test_creates_task_file(
        self,
        sample_topic: TopicConfig,
        vault_root: Path,
        templates_dir: Path,
    ) -> None:
        """TASK 파일 생성"""
        result = scaffold_obsidian_workspace(sample_topic, vault_root, templates_dir)

        assert "task" in result
        task_path = result["task"]
        assert task_path.exists()
        content = task_path.read_text()
        assert "테스트 토픽" in content
        assert "test-topic" in content

    def test_creates_spec_template(
        self,
        sample_topic: TopicConfig,
        vault_root: Path,
        templates_dir: Path,
    ) -> None:
        """SPEC 템플릿 생성"""
        result = scaffold_obsidian_workspace(sample_topic, vault_root, templates_dir)

        assert "spec" in result
        spec_path = result["spec"]
        assert spec_path.exists()
        content = spec_path.read_text()
        assert "테스트 토픽" in content

    def test_idempotent(
        self,
        sample_topic: TopicConfig,
        vault_root: Path,
        templates_dir: Path,
    ) -> None:
        """두번 실행해도 기존 파일 덮어쓰지 않음"""
        result1 = scaffold_obsidian_workspace(sample_topic, vault_root, templates_dir)

        # TASK 파일에 내용 추가
        task_path = result1["task"]
        original = task_path.read_text()
        task_path.write_text(original + "\n## 추가 내용")

        # 두번째 스캐폴딩
        scaffold_obsidian_workspace(sample_topic, vault_root, templates_dir)

        # 기존 파일 보존 확인
        assert "추가 내용" in task_path.read_text()


# ── generate_phase_prompts 테스트 ──


class TestGeneratePhasePrompts:
    """generate_phase_prompts 함수 테스트"""

    def test_generates_prompt_files(
        self,
        sample_topic: TopicConfig,
        vault_root: Path,
        templates_dir: Path,
    ) -> None:
        """프롬프트 파일 생성"""
        prompts = generate_phase_prompts(sample_topic, vault_root, templates_dir)

        assert len(prompts) > 0
        for p in prompts:
            assert p.exists()
            assert p.stat().st_size > 0

    def test_prompts_in_correct_dir(
        self,
        sample_topic: TopicConfig,
        vault_root: Path,
        templates_dir: Path,
    ) -> None:
        """프롬프트 파일이 _prompts/ 디렉토리에 생성"""
        prompts = generate_phase_prompts(sample_topic, vault_root, templates_dir)

        for p in prompts:
            assert p.parent.name == "_prompts"

    def test_gemini_prompt_contains_research(
        self,
        sample_topic: TopicConfig,
        vault_root: Path,
        templates_dir: Path,
    ) -> None:
        """Gemini 프롬프트에 리서치 항목 포함"""
        prompts = generate_phase_prompts(sample_topic, vault_root, templates_dir)

        gemini_prompt = next((p for p in prompts if "gemini" in p.name), None)
        if gemini_prompt:
            content = gemini_prompt.read_text()
            assert "테스트 토픽" in content


# ── get_workflow_status 테스트 ──


class TestGetWorkflowStatus:
    """get_workflow_status 함수 테스트"""

    def test_empty_workspace(
        self,
        sample_topic: TopicConfig,
        vault_root: Path,
    ) -> None:
        """빈 워크스페이스 → intake"""
        base = vault_root / sample_topic.topic.obsidian_base
        base.mkdir(parents=True, exist_ok=True)

        status = get_workflow_status(sample_topic, base)
        assert status["phase"] == "intake"
        assert status["task_file"] is None

    def test_with_task_file(
        self,
        sample_topic: TopicConfig,
        vault_root: Path,
    ) -> None:
        """TASK 파일만 있으면 intake"""
        base = vault_root / sample_topic.topic.obsidian_base
        task_dir = base / "30_Tasks"
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "TASK-test-topic.md").write_text("# TASK")

        status = get_workflow_status(sample_topic, base)
        assert status["phase"] == "intake"
        assert status["task_file"] is not None

    def test_with_research_files(
        self,
        sample_topic: TopicConfig,
        vault_root: Path,
    ) -> None:
        """리서치 파일 존재 → research"""
        base = vault_root / sample_topic.topic.obsidian_base
        task_dir = base / "30_Tasks"
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "TASK-test-topic.md").write_text("# TASK")

        clip_dir = base / "10_Research" / "Clippings"
        clip_dir.mkdir(parents=True, exist_ok=True)
        (clip_dir / "auto-test1.md").write_text("# Clip")

        status = get_workflow_status(sample_topic, base)
        assert status["phase"] == "research"
        assert status["research_pct"] == "1/4"

    def test_with_legacy_research_files(
        self,
        sample_topic: TopicConfig,
        vault_root: Path,
    ) -> None:
        """레거시 07_참고/ 폴더의 리서치 파일도 감지"""
        base = vault_root / sample_topic.topic.obsidian_base
        task_dir = base / "30_Tasks"
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "TASK-test-topic.md").write_text("# TASK")

        ref_dir = base / "07_참고"
        ref_dir.mkdir(parents=True, exist_ok=True)
        (ref_dir / "auto-test1.md").write_text("# Legacy")

        status = get_workflow_status(sample_topic, base)
        assert status["phase"] == "research"
        assert status["research_pct"] == "1/4"

    def test_with_brief(
        self,
        sample_topic: TopicConfig,
        vault_root: Path,
    ) -> None:
        """Brief 존재 → spec"""
        base = vault_root / sample_topic.topic.obsidian_base
        brief_dir = base / "10_Research" / "Briefs"
        brief_dir.mkdir(parents=True, exist_ok=True)
        (brief_dir / "BRIEF-test-topic.md").write_text("# Brief")

        status = get_workflow_status(sample_topic, base)
        assert status["phase"] == "spec"
        assert status["brief_file"] is not None

    def test_with_review(
        self,
        sample_topic: TopicConfig,
        vault_root: Path,
    ) -> None:
        """Review 존재 → done"""
        base = vault_root / sample_topic.topic.obsidian_base
        review_dir = base / "40_Reviews"
        review_dir.mkdir(parents=True, exist_ok=True)
        (review_dir / "REV-test-topic.md").write_text("# Review")

        status = get_workflow_status(sample_topic, base)
        assert status["phase"] == "done"


# ── generate_workflow_status_file 테스트 ──


class TestGenerateWorkflowStatusFile:
    """generate_workflow_status_file 함수 테스트"""

    def test_generates_file(
        self,
        sample_topic: TopicConfig,
        vault_root: Path,
    ) -> None:
        """상태 파일 생성"""
        base = vault_root / sample_topic.topic.obsidian_base
        base.mkdir(parents=True, exist_ok=True)

        output = base / "_workflow-status.md"
        result = generate_workflow_status_file(sample_topic, base, output)

        assert result.exists()
        content = result.read_text()
        assert "테스트 토픽" in content
        assert "Phase" in content
        assert "test-topic" in content

    def test_contains_phase_checklist(
        self,
        sample_topic: TopicConfig,
        vault_root: Path,
    ) -> None:
        """Phase 체크리스트 포함"""
        base = vault_root / sample_topic.topic.obsidian_base
        base.mkdir(parents=True, exist_ok=True)

        output = base / "_workflow-status.md"
        generate_workflow_status_file(sample_topic, base, output)

        content = output.read_text()
        for phase_name in PHASE_NAMES.values():
            assert phase_name in content


# ── WorkflowConfig 하위호환 테스트 ──


class TestWorkflowConfig:
    """WorkflowConfig 하위호환 테스트"""

    def test_optional_workflow(self) -> None:
        """workflow 필드 없어도 TopicConfig 생성 가능"""
        topic = TopicConfig(
            topic=TopicInfo(
                id="compat-test",
                name="호환성 테스트",
                obsidian_base="test/compat",
            ),
        )
        assert topic.workflow is None

    def test_with_workflow(self) -> None:
        """workflow 필드가 있는 TopicConfig"""
        topic = TopicConfig(
            topic=TopicInfo(
                id="wf-test",
                name="워크플로우 테스트",
                obsidian_base="test/wf",
            ),
            workflow=WorkflowConfig(
                obsidian_structure="standard",
                enable_adr=True,
                enable_review=True,
            ),
        )
        assert topic.workflow is not None
        assert topic.workflow.enable_adr is True

    def test_workflow_defaults(self) -> None:
        """WorkflowConfig 기본값"""
        wf = WorkflowConfig()
        assert wf.obsidian_structure == "standard"
        assert wf.enable_adr is True
        assert wf.enable_review is True
        assert wf.review_prompts == []


# ── CLI 서브커맨드 등록 테스트 ──


class TestCLIRegistration:
    """파이프라인 CLI 서브커맨드 등록 테스트"""

    def test_scaffold_command_registered(self) -> None:
        """scaffold 서브커맨드 등록 확인"""
        from ai_env.cli.pipeline_cmd import pipeline

        commands = pipeline.commands
        assert "scaffold" in commands

    def test_workflow_command_registered(self) -> None:
        """workflow 서브커맨드 등록 확인"""
        from ai_env.cli.pipeline_cmd import pipeline

        commands = pipeline.commands
        assert "workflow" in commands


class TestWorkflowStatusAutoUpdate:
    """pipeline workflow 실행 시 상태 파일 자동 갱신 테스트"""

    def test_workflow_command_regenerates_status_file(
        self,
        sample_topic: TopicConfig,
        vault_root: Path,
        templates_dir: Path,
    ) -> None:
        """workflow 명령 실행 시 _workflow-status.md가 자동 재생성됨"""
        # 워크스페이스 스캐폴딩 (30_Tasks 등 생성)
        scaffold_obsidian_workspace(sample_topic, vault_root, templates_dir)

        base = vault_root / sample_topic.topic.obsidian_base
        status_file = base / "_workflow-status.md"

        # 기존 상태 파일에 오래된 내용 작성
        status_file.write_text("# Old status\nphase: intake")
        old_content = status_file.read_text()

        # generate_workflow_status_file 호출 (pipeline_workflow가 하는 것과 동일)
        generate_workflow_status_file(sample_topic, base, status_file)

        new_content = status_file.read_text()
        assert new_content != old_content
        assert "테스트 토픽" in new_content
        assert "Phase" in new_content

    def test_status_file_created_when_tasks_dir_exists(
        self,
        sample_topic: TopicConfig,
        vault_root: Path,
    ) -> None:
        """30_Tasks 디렉토리만 있으면 상태 파일 생성"""
        base = vault_root / sample_topic.topic.obsidian_base
        (base / "30_Tasks").mkdir(parents=True)

        status_file = base / "_workflow-status.md"
        assert not status_file.exists()

        # pipeline_workflow 로직 재현
        if status_file.exists() or (base / "30_Tasks").exists():
            generate_workflow_status_file(sample_topic, base, status_file)

        assert status_file.exists()
        content = status_file.read_text()
        assert "테스트 토픽" in content

    def test_no_status_file_without_workspace(
        self,
        sample_topic: TopicConfig,
        vault_root: Path,
    ) -> None:
        """워크스페이스가 없으면 상태 파일 생성 안 함"""
        base = vault_root / sample_topic.topic.obsidian_base
        base.mkdir(parents=True, exist_ok=True)

        status_file = base / "_workflow-status.md"

        # 30_Tasks도 없고 status_file도 없음 → 생성하지 않음
        if status_file.exists() or (base / "30_Tasks").exists():
            generate_workflow_status_file(sample_topic, base, status_file)

        assert not status_file.exists()


# ── 수동 리서치 워크플로우 상태 ──


class TestWorkflowStatusManualResearch:
    """수동 리서치 파일만 있을 때 워크플로우 상태 테스트"""

    def test_manual_only_research(self, vault_root: Path) -> None:
        """YAML research 비어있고 수동 파일만 → phase=research, manual pct"""
        topic = TopicConfig(
            topic=TopicInfo(
                id="manual-topic",
                name="수동 리서치 토픽",
                obsidian_base="99_Test/manual-topic",
            ),
            research=ResearchConfig(),  # 빈 research
        )
        base = vault_root / topic.topic.obsidian_base
        ref_dir = base / "07_참고"
        ref_dir.mkdir(parents=True)
        (ref_dir / "my-notes.md").write_text("# manual research")
        (ref_dir / "paper-review.md").write_text("# paper")

        status = get_workflow_status(topic, base)
        assert status["phase"] == "research"
        assert "manual" in status["research_pct"]
        assert status["research_pct"] == "2/2 (manual)"

    def test_manual_in_clippings(self, vault_root: Path) -> None:
        """10_Research/Clippings/에 수동 파일 → phase=research"""
        topic = TopicConfig(
            topic=TopicInfo(
                id="clip-topic",
                name="Clippings 토픽",
                obsidian_base="99_Test/clip-topic",
            ),
            research=ResearchConfig(),
        )
        base = vault_root / topic.topic.obsidian_base
        clip_dir = base / "10_Research" / "Clippings"
        clip_dir.mkdir(parents=True)
        (clip_dir / "article.md").write_text("# article")

        status = get_workflow_status(topic, base)
        assert status["phase"] == "research"
        assert status["research_pct"] == "1/1 (manual)"
