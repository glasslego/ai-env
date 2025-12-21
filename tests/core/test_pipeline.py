"""토픽 기반 3-Track 리서치 파이프라인 테스트"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from ai_env.core.pipeline import (
    collect_research_files,
    generate_deep_research_prompt_file,
    generate_research_status,
    get_obsidian_base_path,
    get_research_completion_status,
    list_topics,
    load_deep_research_prompts,
    load_topic,
    validate_topic_for_phase,
)

# ── Fixtures ──


@pytest.fixture()
def sample_topic_yaml(tmp_path: Path) -> Path:
    """샘플 토픽 YAML 파일 생성"""
    topics_dir = tmp_path / "config" / "topics"
    topics_dir.mkdir(parents=True)

    topic_data = {
        "topic": {
            "id": "test-topic",
            "name": "테스트 토픽",
            "obsidian_base": "51_자동화시스템/99_테스트",
            "project_repo": "~/work/test-project",
        },
        "research": {
            "auto": [
                {"query": "python async best practices", "output": "07_참고/auto-async.md"},
                {"query": "pytest fixtures guide", "output": "07_참고/auto-pytest.md"},
            ],
            "gemini_deep": [
                {
                    "prompt": "Gemini 심층리서치 프롬프트 내용",
                    "output": "07_참고/gemini-deep-test.md",
                    "focus": "테스트 초점",
                }
            ],
            "gpt_deep": [
                {
                    "prompt": "GPT 심층리서치 프롬프트 내용",
                    "output": "07_참고/gpt-deep-test.md",
                    "focus": "학술 분석",
                }
            ],
        },
        "plan": {
            "synthesis_prompt": "리서치 종합하여 spec 작성",
            "output": "01_시스템구성/plan-spec.md",
        },
        "code": {
            "style": "tdd",
            "target_repo": "~/work/test-project",
            "test_framework": "pytest",
            "modules": [
                {"name": "core", "desc": "핵심 모듈"},
                {"name": "api", "desc": "API 모듈"},
            ],
        },
    }

    yaml_path = topics_dir / "test-topic.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(topic_data, f, allow_unicode=True)

    return topics_dir


@pytest.fixture()
def sample_topic_minimal_yaml(tmp_path: Path) -> Path:
    """코드 섹션 없는 최소 토픽 YAML"""
    topics_dir = tmp_path / "config" / "topics"
    topics_dir.mkdir(parents=True)

    topic_data = {
        "topic": {
            "id": "minimal-topic",
            "name": "최소 토픽",
            "obsidian_base": "99_테스트",
        },
        "research": {
            "auto": [
                {"query": "test query", "output": "07_참고/auto-test.md"},
            ],
        },
    }

    yaml_path = topics_dir / "minimal-topic.yaml"
    with open(yaml_path, "w") as f:
        yaml.dump(topic_data, f, allow_unicode=True)

    return topics_dir


# ── TopicConfig 로드 테스트 ──


class TestLoadTopic:
    def test_load_full_topic(self, sample_topic_yaml: Path) -> None:
        """전체 필드가 있는 토픽 로드"""
        topic = load_topic("test-topic", sample_topic_yaml)

        assert topic.topic.id == "test-topic"
        assert topic.topic.name == "테스트 토픽"
        assert topic.topic.obsidian_base == "51_자동화시스템/99_테스트"
        assert topic.topic.project_repo == "~/work/test-project"

    def test_load_research_tracks(self, sample_topic_yaml: Path) -> None:
        """3-Track 리서치 항목 로드"""
        topic = load_topic("test-topic", sample_topic_yaml)

        assert len(topic.research.auto) == 2
        assert len(topic.research.gemini_deep) == 1
        assert len(topic.research.gpt_deep) == 1

        assert topic.research.auto[0].query == "python async best practices"
        assert topic.research.gemini_deep[0].focus == "테스트 초점"

    def test_load_plan_section(self, sample_topic_yaml: Path) -> None:
        """plan 섹션 로드"""
        topic = load_topic("test-topic", sample_topic_yaml)

        assert topic.plan is not None
        assert "spec 작성" in topic.plan.synthesis_prompt
        assert topic.plan.output == "01_시스템구성/plan-spec.md"

    def test_load_code_section(self, sample_topic_yaml: Path) -> None:
        """code 섹션 로드"""
        topic = load_topic("test-topic", sample_topic_yaml)

        assert topic.code is not None
        assert topic.code.style == "tdd"
        assert topic.code.test_framework == "pytest"
        assert len(topic.code.modules) == 2

    def test_load_minimal_topic(self, sample_topic_minimal_yaml: Path) -> None:
        """최소 토픽 (research.auto만) 로드"""
        topic = load_topic("minimal-topic", sample_topic_minimal_yaml)

        assert topic.topic.id == "minimal-topic"
        assert len(topic.research.auto) == 1
        assert topic.research.gemini_deep == []
        assert topic.research.gpt_deep == []
        assert topic.plan is None
        assert topic.code is None

    def test_load_nonexistent_topic(self, tmp_path: Path) -> None:
        """존재하지 않는 토픽 로드 시 에러"""
        topics_dir = tmp_path / "config" / "topics"
        topics_dir.mkdir(parents=True)

        with pytest.raises(FileNotFoundError):
            load_topic("nonexistent", topics_dir)


# ── 토픽 목록 조회 ──


class TestListTopics:
    def test_list_topics(self, sample_topic_yaml: Path) -> None:
        """토픽 목록 조회"""
        topics = list_topics(sample_topic_yaml)
        assert "test-topic" in topics

    def test_list_topics_empty_dir(self, tmp_path: Path) -> None:
        """빈 디렉토리"""
        topics_dir = tmp_path / "config" / "topics"
        topics_dir.mkdir(parents=True)
        assert list_topics(topics_dir) == []


# ── Obsidian 경로 ──


class TestObsidianPath:
    def test_get_obsidian_base_path(self, sample_topic_yaml: Path) -> None:
        """Obsidian 기본 경로 생성"""
        topic = load_topic("test-topic", sample_topic_yaml)
        vault_root = Path("/Users/megan/Documents/Obsidian Vault")
        path = get_obsidian_base_path(topic, vault_root)

        assert path == vault_root / "51_자동화시스템" / "99_테스트"


# ── 심층리서치 프롬프트 파일 생성 ──


class TestDeepResearchPrompts:
    def test_generate_gemini_prompt_file(self, sample_topic_yaml: Path, tmp_path: Path) -> None:
        """Gemini 심층리서치 프롬프트 파일 생성"""
        topic = load_topic("test-topic", sample_topic_yaml)
        output_dir = tmp_path / "07_참고"
        output_dir.mkdir(parents=True)

        result = generate_deep_research_prompt_file(
            items=topic.research.gemini_deep,
            tool_name="Gemini",
            output_path=output_dir / "_gemini-prompts.md",
            topic_name=topic.topic.name,
        )

        assert result.exists()
        content = result.read_text()
        assert "Gemini" in content
        assert "심층리서치 프롬프트 내용" in content
        assert "gemini-deep-test.md" in content

    def test_generate_gpt_prompt_file(self, sample_topic_yaml: Path, tmp_path: Path) -> None:
        """GPT 심층리서치 프롬프트 파일 생성"""
        topic = load_topic("test-topic", sample_topic_yaml)
        output_dir = tmp_path / "07_참고"
        output_dir.mkdir(parents=True)

        result = generate_deep_research_prompt_file(
            items=topic.research.gpt_deep,
            tool_name="GPT",
            output_path=output_dir / "_gpt-prompts.md",
            topic_name=topic.topic.name,
        )

        assert result.exists()
        content = result.read_text()
        assert "GPT" in content
        assert "학술 분석" in content


# ── 리서치 상태 체크리스트 ──


class TestResearchStatus:
    def test_generate_status_file(self, sample_topic_yaml: Path, tmp_path: Path) -> None:
        """리서치 상태 체크리스트 생성"""
        topic = load_topic("test-topic", sample_topic_yaml)
        output_path = tmp_path / "_research-status.md"

        # Track A 결과 중 하나만 존재하는 상황 시뮬레이션
        existing_files = {"07_참고/auto-async.md"}

        result = generate_research_status(
            topic=topic,
            output_path=output_path,
            existing_files=existing_files,
        )

        assert result.exists()
        content = result.read_text()
        assert "[x]" in content  # auto-async.md 완료
        assert "[ ]" in content  # 나머지 미완료
        assert "wf-spec" in content  # 다음 단계 안내


# ── 리서치 완료 상태 확인 ──


class TestResearchCompletionStatus:
    def test_all_missing(self, sample_topic_yaml: Path, tmp_path: Path) -> None:
        """모든 파일이 없는 경우"""
        topic = load_topic("test-topic", sample_topic_yaml)
        obsidian_base = tmp_path / "vault" / "51_자동화시스템" / "99_테스트"
        obsidian_base.mkdir(parents=True)

        status = get_research_completion_status(topic, obsidian_base)

        assert len(status["track_a"]) == 2
        assert all(not exists for _, exists in status["track_a"])
        assert len(status["track_b"]) == 1
        assert len(status["track_c"]) == 1

    def test_partial_complete(self, sample_topic_yaml: Path, tmp_path: Path) -> None:
        """일부 파일만 존재하는 경우"""
        topic = load_topic("test-topic", sample_topic_yaml)
        obsidian_base = tmp_path / "vault" / "51_자동화시스템" / "99_테스트"

        # Track A의 첫 번째 파일만 생성
        auto_file = obsidian_base / "07_참고" / "auto-async.md"
        auto_file.parent.mkdir(parents=True)
        auto_file.write_text("# test")

        status = get_research_completion_status(topic, obsidian_base)

        assert status["track_a"][0] == ("07_참고/auto-async.md", True)
        assert status["track_a"][1] == ("07_참고/auto-pytest.md", False)

    def test_all_complete(self, sample_topic_yaml: Path, tmp_path: Path) -> None:
        """모든 파일이 존재하는 경우"""
        topic = load_topic("test-topic", sample_topic_yaml)
        obsidian_base = tmp_path / "vault" / "51_자동화시스템" / "99_테스트"
        ref_dir = obsidian_base / "07_참고"
        ref_dir.mkdir(parents=True)

        # 모든 파일 생성
        for name in ["auto-async.md", "auto-pytest.md", "gemini-deep-test.md", "gpt-deep-test.md"]:
            (ref_dir / name).write_text("# test")

        status = get_research_completion_status(topic, obsidian_base)

        assert all(exists for _, exists in status["track_a"])
        assert all(exists for _, exists in status["track_b"])
        assert all(exists for _, exists in status["track_c"])

    def test_minimal_topic(self, sample_topic_minimal_yaml: Path, tmp_path: Path) -> None:
        """최소 토픽 (gemini/gpt 없음)"""
        topic = load_topic("minimal-topic", sample_topic_minimal_yaml)
        obsidian_base = tmp_path / "vault"

        status = get_research_completion_status(topic, obsidian_base)

        assert len(status["track_a"]) == 1
        assert len(status["track_b"]) == 0
        assert len(status["track_c"]) == 0


# ── Phase 유효성 검증 ──


class TestValidateTopicForPhase:
    def test_research_valid(self, sample_topic_yaml: Path) -> None:
        """research phase 유효성 — 정상"""
        topic = load_topic("test-topic", sample_topic_yaml)
        is_valid, msg = validate_topic_for_phase(topic, "research")
        assert is_valid

    def test_synthesize_valid(self, sample_topic_yaml: Path) -> None:
        """synthesize phase 유효성 — 정상"""
        topic = load_topic("test-topic", sample_topic_yaml)
        is_valid, msg = validate_topic_for_phase(topic, "synthesize")
        assert is_valid

    def test_code_valid(self, sample_topic_yaml: Path) -> None:
        """code phase 유효성 — 정상"""
        topic = load_topic("test-topic", sample_topic_yaml)
        is_valid, msg = validate_topic_for_phase(topic, "code")
        assert is_valid

    def test_code_no_section(self, sample_topic_minimal_yaml: Path) -> None:
        """code phase — code 섹션 없음"""
        topic = load_topic("minimal-topic", sample_topic_minimal_yaml)
        is_valid, msg = validate_topic_for_phase(topic, "code")
        assert not is_valid
        assert "code 섹션" in msg

    def test_synthesize_no_plan(self, sample_topic_minimal_yaml: Path) -> None:
        """synthesize phase — plan 섹션 없음"""
        topic = load_topic("minimal-topic", sample_topic_minimal_yaml)
        is_valid, msg = validate_topic_for_phase(topic, "synthesize")
        assert not is_valid
        assert "plan 섹션" in msg

    def test_unknown_phase(self, sample_topic_yaml: Path) -> None:
        """알 수 없는 phase"""
        topic = load_topic("test-topic", sample_topic_yaml)
        is_valid, msg = validate_topic_for_phase(topic, "unknown")
        assert not is_valid


# ── CLI 등록 확인 ──


class TestCLIRegistration:
    def test_pipeline_group_registered(self) -> None:
        """pipeline 그룹이 main CLI에 등록되었는지 확인"""
        from ai_env.cli import main

        commands = main.commands
        assert "pipeline" in commands, "pipeline 그룹이 CLI에 등록되지 않았습니다"

    def test_pipeline_subcommands(self) -> None:
        """pipeline 하위 커맨드들이 등록되었는지 확인"""
        from ai_env.cli.pipeline_cmd import pipeline

        commands = pipeline.commands
        assert "list" in commands
        assert "info" in commands
        assert "research" in commands
        assert "status" in commands
        assert "dispatch" in commands


# ── Deep Research 프롬프트 매핑 ──


class TestLoadDeepResearchPrompts:
    @pytest.fixture()
    def prompts_dir(self, tmp_path: Path) -> Path:
        """프롬프트 MD 파일이 있는 디렉토리"""
        topic_dir = tmp_path / "config" / "prompts" / "bitcoin-automation"
        topic_dir.mkdir(parents=True)

        (topic_dir / "gemini-trend.md").write_text(
            "---\n"
            "track: gemini\n"
            'output: "07_참고/gemini-deep-trend.md"\n'
            'focus: "최신 트렌드"\n'
            "---\n\n"
            "비트코인 트렌드 조사",
            encoding="utf-8",
        )
        (topic_dir / "gpt-quant.md").write_text(
            "---\n"
            "track: gpt\n"
            'output: "07_참고/gpt-deep-quant.md"\n'
            'focus: "퀀트 전략"\n'
            "---\n\n"
            "퀀트 전략 분석",
            encoding="utf-8",
        )

        return tmp_path / "config" / "prompts"

    def test_load_existing_topic(self, prompts_dir: Path) -> None:
        """존재하는 topic_id의 프롬프트 로드"""
        result = load_deep_research_prompts("bitcoin-automation", prompts_dir)

        assert result is not None
        assert len(result.gemini_deep) == 1
        assert len(result.gpt_deep) == 1
        assert result.gemini_deep[0].prompt == "비트코인 트렌드 조사"
        assert result.gemini_deep[0].focus == "최신 트렌드"
        assert result.gpt_deep[0].output == "07_참고/gpt-deep-quant.md"

    def test_load_nonexistent_topic(self, prompts_dir: Path) -> None:
        """존재하지 않는 topic_id → None"""
        result = load_deep_research_prompts("nonexistent-topic", prompts_dir)
        assert result is None

    def test_load_no_prompts_dir(self, tmp_path: Path) -> None:
        """prompts 디렉토리 자체가 없을 때 → None"""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        result = load_deep_research_prompts("bitcoin-automation", empty_dir)
        assert result is None

    def test_load_empty_topic_dir(self, tmp_path: Path) -> None:
        """토픽 디렉토리에 MD 파일이 없을 때 → None"""
        topic_dir = tmp_path / "prompts" / "empty-topic"
        topic_dir.mkdir(parents=True)

        result = load_deep_research_prompts("empty-topic", tmp_path / "prompts")
        assert result is None

    def test_load_topic_gemini_only(self, tmp_path: Path) -> None:
        """Gemini만 있는 토픽 → gpt_deep 빈 리스트"""
        topic_dir = tmp_path / "prompts" / "my-topic"
        topic_dir.mkdir(parents=True)

        (topic_dir / "gemini-research.md").write_text(
            '---\ntrack: gemini\noutput: "07_참고/gemini.md"\n---\n\n조사 프롬프트',
            encoding="utf-8",
        )

        result = load_deep_research_prompts("my-topic", tmp_path / "prompts")
        assert result is not None
        assert len(result.gemini_deep) == 1
        assert result.gpt_deep == []

    def test_skip_invalid_frontmatter(self, tmp_path: Path) -> None:
        """frontmatter 없거나 track/output 누락 → 스킵"""
        topic_dir = tmp_path / "prompts" / "bad-topic"
        topic_dir.mkdir(parents=True)

        # track 누락
        (topic_dir / "no-track.md").write_text(
            '---\noutput: "07_참고/test.md"\n---\n\n프롬프트',
            encoding="utf-8",
        )
        # frontmatter 없음
        (topic_dir / "no-frontmatter.md").write_text(
            "그냥 텍스트",
            encoding="utf-8",
        )

        result = load_deep_research_prompts("bad-topic", tmp_path / "prompts")
        assert result is None

    def test_multiline_prompt_body(self, tmp_path: Path) -> None:
        """여러 줄 프롬프트 본문 정상 파싱"""
        topic_dir = tmp_path / "prompts" / "multi"
        topic_dir.mkdir(parents=True)

        body = "첫 번째 줄\n\n두 번째 문단\n\n1. 항목 1\n2. 항목 2"
        (topic_dir / "gemini-test.md").write_text(
            '---\ntrack: gemini\noutput: "07_참고/gemini.md"\nfocus: "테스트"\n---\n\n' + body,
            encoding="utf-8",
        )

        result = load_deep_research_prompts("multi", tmp_path / "prompts")
        assert result is not None
        assert result.gemini_deep[0].prompt == body


# ── 수동 리서치 + dual dir 지원 ──


class TestCollectResearchFilesManual:
    def test_manual_files_classified(self, tmp_path: Path) -> None:
        """패턴에 안 맞는 .md 파일은 manual 트랙으로 분류"""
        obsidian_base = tmp_path / "vault"
        ref_dir = obsidian_base / "07_참고"
        ref_dir.mkdir(parents=True)

        (ref_dir / "auto-search.md").write_text("# auto")
        (ref_dir / "gemini-deep.md").write_text("# gemini")
        (ref_dir / "gpt-deep.md").write_text("# gpt")
        (ref_dir / "my-notes.md").write_text("# notes")
        (ref_dir / "paper-summary.md").write_text("# paper")
        (ref_dir / "_status.md").write_text("# meta")  # 제외 대상

        result = collect_research_files(obsidian_base)

        assert len(result["track_a"]) == 1
        assert len(result["track_b"]) == 1
        assert len(result["track_c"]) == 1
        assert len(result["manual"]) == 2
        assert {f.name for f in result["manual"]} == {"my-notes.md", "paper-summary.md"}

    def test_both_dirs_searched(self, tmp_path: Path) -> None:
        """07_참고/ 와 10_Research/Clippings/ 모두 탐색"""
        obsidian_base = tmp_path / "vault"
        ref_dir = obsidian_base / "07_참고"
        clip_dir = obsidian_base / "10_Research" / "Clippings"
        ref_dir.mkdir(parents=True)
        clip_dir.mkdir(parents=True)

        (ref_dir / "auto-test.md").write_text("# ref auto")
        (clip_dir / "gemini-test.md").write_text("# clip gemini")
        (clip_dir / "research-notes.md").write_text("# clip manual")

        result = collect_research_files(obsidian_base)

        assert len(result["track_a"]) == 1
        assert len(result["track_b"]) == 1
        assert len(result["manual"]) == 1

    def test_empty_dirs(self, tmp_path: Path) -> None:
        """디렉토리가 없을 때 빈 결과"""
        obsidian_base = tmp_path / "vault"
        obsidian_base.mkdir(parents=True)

        result = collect_research_files(obsidian_base)

        assert result == {"track_a": [], "track_b": [], "track_c": [], "manual": []}

    def test_manual_key_always_present(self, tmp_path: Path) -> None:
        """수동 파일이 없어도 manual 키가 존재"""
        obsidian_base = tmp_path / "vault"
        ref_dir = obsidian_base / "07_참고"
        ref_dir.mkdir(parents=True)

        (ref_dir / "auto-test.md").write_text("# auto")

        result = collect_research_files(obsidian_base)
        assert "manual" in result
        assert len(result["manual"]) == 0


class TestCompletionStatusManual:
    def test_includes_manual_files(self, sample_topic_yaml: Path, tmp_path: Path) -> None:
        """completion status에 수동 파일이 포함"""
        topic = load_topic("test-topic", sample_topic_yaml)
        obsidian_base = tmp_path / "vault" / "51_자동화시스템" / "99_테스트"
        ref_dir = obsidian_base / "07_참고"
        ref_dir.mkdir(parents=True)

        (ref_dir / "manual-notes.md").write_text("# notes")

        status = get_research_completion_status(topic, obsidian_base)

        assert "manual" in status
        assert len(status["manual"]) == 1
        assert status["manual"][0][1] is True  # 존재하는 파일이므로 True


class TestValidateSynthesizeWithDiskFiles:
    @pytest.fixture()
    def topic_no_research(self, tmp_path: Path) -> Path:
        """research 없고 plan만 있는 토픽"""
        topics_dir = tmp_path / "config" / "topics"
        topics_dir.mkdir(parents=True)

        topic_data = {
            "topic": {
                "id": "manual-only",
                "name": "수동 리서치 토픽",
                "obsidian_base": "99_test",
            },
            "plan": {
                "synthesis_prompt": "종합",
                "output": "spec.md",
            },
        }

        yaml_path = topics_dir / "manual-only.yaml"
        with open(yaml_path, "w") as f:
            yaml.dump(topic_data, f, allow_unicode=True)

        return topics_dir

    def test_disk_files_allow_synthesize(self, topic_no_research: Path, tmp_path: Path) -> None:
        """YAML research 비어있어도 디스크에 파일 있으면 synthesize 통과"""
        topic = load_topic("manual-only", topic_no_research)
        obsidian_base = tmp_path / "vault" / "99_test"
        ref_dir = obsidian_base / "07_참고"
        ref_dir.mkdir(parents=True)
        (ref_dir / "my-research.md").write_text("# research")

        is_valid, msg = validate_topic_for_phase(topic, "synthesize", obsidian_base=obsidian_base)
        assert is_valid

    def test_no_disk_files_block_synthesize(self, topic_no_research: Path, tmp_path: Path) -> None:
        """YAML research 비어있고 디스크에도 파일 없으면 synthesize 차단"""
        topic = load_topic("manual-only", topic_no_research)
        obsidian_base = tmp_path / "vault" / "99_test"
        obsidian_base.mkdir(parents=True)

        is_valid, msg = validate_topic_for_phase(topic, "synthesize", obsidian_base=obsidian_base)
        assert not is_valid

    def test_backward_compat_no_obsidian_base(self, topic_no_research: Path) -> None:
        """obsidian_base 없이 호출하면 기존 동작 (YAML만 체크)"""
        topic = load_topic("manual-only", topic_no_research)

        is_valid, msg = validate_topic_for_phase(topic, "synthesize")
        assert not is_valid
        assert "리서치 결과가 없습니다" in msg
