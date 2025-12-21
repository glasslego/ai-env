"""Deep Research API 디스패치 테스트

httpx mock으로 Gemini/OpenAI API 호출을 테스트한다.
실제 API는 호출하지 않음.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from ai_env.core.pipeline import (
    DeepResearchItem,
    ResearchConfig,
    TopicConfig,
    TopicInfo,
)
from ai_env.core.research import (
    DeepResearchResult,
    _extract_gemini_content,
    _extract_gemini_sources,
    _extract_openai_content,
    _extract_openai_sources,
    dispatch_deep_research,
    dispatch_gemini_deep_research,
    dispatch_openai_deep_research,
    format_result_markdown,
)

# ── Fixtures ──


@pytest.fixture()
def sample_topic() -> TopicConfig:
    """테스트용 토픽 설정"""
    return TopicConfig(
        topic=TopicInfo(
            id="test-topic",
            name="테스트 토픽",
            obsidian_base="99_테스트",
        ),
        research=ResearchConfig(
            gemini_deep=[
                DeepResearchItem(
                    prompt="Gemini 리서치 프롬프트",
                    output="07_참고/gemini-deep-test.md",
                    focus="테스트 포커스",
                ),
            ],
            gpt_deep=[
                DeepResearchItem(
                    prompt="GPT 리서치 프롬프트",
                    output="07_참고/gpt-deep-test.md",
                    focus="GPT 테스트",
                ),
            ],
        ),
    )


# ── DeepResearchResult 모델 테스트 ──


class TestDeepResearchResult:
    def test_success_result(self):
        r = DeepResearchResult(
            provider="gemini",
            prompt="test",
            output_path="07_참고/result.md",
            content="리서치 결과",
            elapsed_seconds=30.5,
        )
        assert r.provider == "gemini"
        assert r.content == "리서치 결과"
        assert r.error is None
        assert r.sources == []

    def test_error_result(self):
        r = DeepResearchResult(
            provider="openai",
            prompt="test",
            output_path="",
            error="API 에러",
            elapsed_seconds=1.0,
        )
        assert r.content is None
        assert r.error == "API 에러"

    def test_sources_field(self):
        r = DeepResearchResult(
            provider="gemini",
            prompt="test",
            output_path="",
            content="결과",
            sources=["https://example.com/1", "https://example.com/2"],
            elapsed_seconds=10.0,
        )
        assert len(r.sources) == 2


# ── Gemini 콘텐츠 추출 테스트 ──


class TestGeminiExtract:
    def test_extract_content_from_output(self):
        data = {"output": {"content": {"parts": [{"text": "파트1"}, {"text": "파트2"}]}}}
        assert _extract_gemini_content(data) == "파트1\n\n파트2"

    def test_extract_content_from_candidates(self):
        data = {"candidates": [{"content": {"parts": [{"text": "후보 텍스트"}]}}]}
        assert _extract_gemini_content(data) == "후보 텍스트"

    def test_extract_content_from_response(self):
        data = {"response": {"text": "응답 텍스트"}}
        assert _extract_gemini_content(data) == "응답 텍스트"

    def test_extract_content_fallback(self):
        data = {"unknown": "field"}
        result = _extract_gemini_content(data)
        assert "unknown" in result  # str(data) 반환

    def test_extract_sources_from_grounding(self):
        data = {
            "candidates": [
                {
                    "groundingMetadata": {
                        "groundingChunks": [
                            {"web": {"uri": "https://example.com/1", "title": "T1"}},
                            {"web": {"uri": "https://example.com/2", "title": "T2"}},
                        ]
                    }
                }
            ]
        }
        assert _extract_gemini_sources(data) == [
            "https://example.com/1",
            "https://example.com/2",
        ]

    def test_extract_sources_from_output(self):
        data = {
            "output": {
                "sources": [
                    {"uri": "https://a.com"},
                    {"url": "https://b.com"},
                ]
            }
        }
        assert _extract_gemini_sources(data) == [
            "https://a.com",
            "https://b.com",
        ]

    def test_extract_sources_empty(self):
        assert _extract_gemini_sources({}) == []


# ── OpenAI 콘텐츠 추출 테스트 ──


class TestOpenAIExtract:
    def test_extract_content_from_output_message(self):
        data = {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "OpenAI 결과"}],
                }
            ]
        }
        assert _extract_openai_content(data) == "OpenAI 결과"

    def test_extract_content_from_text(self):
        data = {"text": "직접 텍스트"}
        assert _extract_openai_content(data) == "직접 텍스트"

    def test_extract_content_empty(self):
        assert _extract_openai_content({}) == ""

    def test_extract_sources_from_web_search(self):
        data = {
            "output": [
                {"type": "web_search_call", "url": "https://search1.com"},
                {"type": "web_search_call", "url": "https://search2.com"},
                {"type": "message", "content": []},
            ]
        }
        assert _extract_openai_sources(data) == [
            "https://search1.com",
            "https://search2.com",
        ]

    def test_extract_sources_empty(self):
        assert _extract_openai_sources({}) == []


# ── format_result_markdown 테스트 ──


class TestFormatResultMarkdown:
    def test_success_format(self):
        result = DeepResearchResult(
            provider="gemini",
            prompt="test",
            output_path="07_참고/gemini.md",
            content="# 리서치 결과\n\n상세 내용",
            sources=["https://src.com"],
            elapsed_seconds=120.0,
        )
        md = format_result_markdown(result, topic_id="bitcoin", focus="트렌드 분석")

        assert "source: Gemini Deep Research (API)" in md
        assert "track: B" in md
        assert "topic: bitcoin" in md
        assert "elapsed: 120s" in md
        assert "# 트렌드 분석" in md
        assert "# 리서치 결과" in md
        assert "https://src.com" in md

    def test_error_format(self):
        result = DeepResearchResult(
            provider="openai",
            prompt="test",
            output_path="",
            error="HTTP 429",
            elapsed_seconds=1.0,
        )
        md = format_result_markdown(result, topic_id="test")

        assert "source: GPT Deep Research (API)" in md
        assert "track: C" in md
        assert "HTTP 429" in md

    def test_no_focus(self):
        result = DeepResearchResult(
            provider="gemini",
            prompt="test",
            output_path="",
            content="결과",
            elapsed_seconds=10.0,
        )
        md = format_result_markdown(result, topic_id="test")
        assert "# Gemini Deep Research 리서치 결과" in md


# ── Gemini API 호출 테스트 (httpx mock) ──


class TestGeminiDispatch:
    @pytest.mark.asyncio()
    async def test_gemini_start_research(self):
        """POST 요청 후 polling → 완료"""
        with patch("ai_env.core.research.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            # POST 응답 (json()은 동기 메서드)
            mock_post_resp = MagicMock()
            mock_post_resp.json.return_value = {"id": "interaction-123", "state": "ACTIVE"}
            mock_post_resp.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_post_resp)

            # GET 응답 (polling)
            mock_get_resp = MagicMock()
            mock_get_resp.json.return_value = {
                "state": "COMPLETED",
                "output": {"content": {"parts": [{"text": "Gemini 리서치 결과"}]}},
            }
            mock_get_resp.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_get_resp)

            mock_client_cls.return_value = mock_client

            with patch("ai_env.core.research.asyncio.sleep", new_callable=AsyncMock):
                result = await dispatch_gemini_deep_research(
                    prompt="테스트 프롬프트",
                    api_key="test-key",
                    poll_interval=0,
                    timeout=60,
                )

        assert result.provider == "gemini"
        assert result.content == "Gemini 리서치 결과"
        assert result.error is None

    @pytest.mark.asyncio()
    async def test_gemini_api_error(self):
        """API HTTP 에러 처리"""
        with patch("ai_env.core.research.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            mock_resp = MagicMock()
            mock_resp.status_code = 403
            mock_resp.text = "Forbidden"
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Forbidden",
                request=httpx.Request("POST", "https://test.com"),
                response=httpx.Response(403, text="Forbidden"),
            )
            mock_client.post = AsyncMock(return_value=mock_resp)

            mock_client_cls.return_value = mock_client

            result = await dispatch_gemini_deep_research(prompt="test", api_key="bad-key")

        assert result.provider == "gemini"
        assert result.error is not None
        assert "403" in result.error

    @pytest.mark.asyncio()
    async def test_gemini_timeout(self):
        """폴링 타임아웃"""
        with patch("ai_env.core.research.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            # POST 성공
            mock_post_resp = MagicMock()
            mock_post_resp.json.return_value = {"id": "id-1", "state": "ACTIVE"}
            mock_post_resp.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_post_resp)

            # GET: 항상 ACTIVE
            mock_get_resp = MagicMock()
            mock_get_resp.json.return_value = {"state": "ACTIVE"}
            mock_get_resp.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_get_resp)

            mock_client_cls.return_value = mock_client

            with patch("ai_env.core.research.asyncio.sleep", new_callable=AsyncMock):
                result = await dispatch_gemini_deep_research(
                    prompt="test", api_key="key", poll_interval=0, timeout=0
                )

        assert "타임아웃" in result.error

    @pytest.mark.asyncio()
    async def test_gemini_polling_4xx_early_exit(self):
        """Polling 중 4xx 에러(인증/권한)는 재시도 없이 즉시 실패"""
        with patch("ai_env.core.research.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            # POST 성공
            mock_post_resp = MagicMock()
            mock_post_resp.json.return_value = {"id": "id-auth", "state": "ACTIVE"}
            mock_post_resp.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_post_resp)

            # GET: 401 에러
            mock_get_resp = MagicMock()
            mock_get_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Unauthorized",
                request=httpx.Request("GET", "https://test.com"),
                response=httpx.Response(401, text="Unauthorized"),
            )
            mock_client.get = AsyncMock(return_value=mock_get_resp)

            mock_client_cls.return_value = mock_client

            with patch("ai_env.core.research.asyncio.sleep", new_callable=AsyncMock):
                result = await dispatch_gemini_deep_research(
                    prompt="test", api_key="bad-key", poll_interval=0, timeout=60
                )

        assert result.error is not None
        assert "401" in result.error
        # 1회 GET만 호출 (재시도 없이 즉시 실패)
        assert mock_client.get.call_count == 1

    @pytest.mark.asyncio()
    async def test_gemini_polling_5xx_retries(self):
        """Polling 중 5xx 에러는 재시도"""
        with patch("ai_env.core.research.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            # POST 성공
            mock_post_resp = MagicMock()
            mock_post_resp.json.return_value = {"id": "id-5xx", "state": "ACTIVE"}
            mock_post_resp.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_post_resp)

            # GET: 첫 번째 500 에러 → 두 번째 성공
            error_resp = MagicMock()
            error_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server Error",
                request=httpx.Request("GET", "https://test.com"),
                response=httpx.Response(500, text="Internal Server Error"),
            )
            success_resp = MagicMock()
            success_resp.json.return_value = {
                "state": "COMPLETED",
                "output": {"content": {"parts": [{"text": "결과"}]}},
            }
            success_resp.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(side_effect=[error_resp, success_resp])

            mock_client_cls.return_value = mock_client

            with patch("ai_env.core.research.asyncio.sleep", new_callable=AsyncMock):
                result = await dispatch_gemini_deep_research(
                    prompt="test", api_key="key", poll_interval=0, timeout=60
                )

        assert result.content == "결과"
        assert result.error is None
        # 5xx 후 재시도하여 2번 호출
        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio()
    async def test_gemini_failed_state(self):
        """리서치 FAILED 상태"""
        with patch("ai_env.core.research.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            mock_post_resp = MagicMock()
            mock_post_resp.json.return_value = {"id": "id-2", "state": "ACTIVE"}
            mock_post_resp.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_post_resp)

            mock_get_resp = MagicMock()
            mock_get_resp.json.return_value = {"state": "FAILED", "error": "internal"}
            mock_get_resp.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_get_resp)

            mock_client_cls.return_value = mock_client

            with patch("ai_env.core.research.asyncio.sleep", new_callable=AsyncMock):
                result = await dispatch_gemini_deep_research(
                    prompt="test", api_key="key", poll_interval=0, timeout=60
                )

        assert "FAILED" in result.error


# ── OpenAI API 호출 테스트 ──


class TestOpenAIDispatch:
    @pytest.mark.asyncio()
    async def test_openai_dispatch_success(self):
        """성공적인 응답"""
        with patch("ai_env.core.research.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "status": "completed",
                "output": [
                    {
                        "type": "web_search_call",
                        "url": "https://source.com",
                    },
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": "OpenAI 리서치 결과"},
                        ],
                    },
                ],
            }
            mock_resp.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_resp)

            mock_client_cls.return_value = mock_client

            result = await dispatch_openai_deep_research(
                prompt="테스트 프롬프트", api_key="test-key"
            )

        assert result.provider == "openai"
        assert result.content == "OpenAI 리서치 결과"
        assert "https://source.com" in result.sources
        assert result.error is None

    @pytest.mark.asyncio()
    async def test_openai_api_error(self):
        """API HTTP 에러"""
        with patch("ai_env.core.research.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            mock_resp = MagicMock()
            mock_resp.status_code = 429
            mock_resp.text = "Rate limited"
            mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Rate limited",
                request=httpx.Request("POST", "https://test.com"),
                response=httpx.Response(429, text="Rate limited"),
            )
            mock_client.post = AsyncMock(return_value=mock_resp)

            mock_client_cls.return_value = mock_client

            result = await dispatch_openai_deep_research(prompt="test", api_key="bad-key")

        assert result.error is not None
        assert "429" in result.error

    @pytest.mark.asyncio()
    async def test_openai_polling_4xx_early_exit(self):
        """Polling 중 4xx 에러는 재시도 없이 즉시 실패"""
        with patch("ai_env.core.research.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            # POST: incomplete → polling 진입
            mock_post_resp = MagicMock()
            mock_post_resp.json.return_value = {"id": "resp-123", "status": "incomplete"}
            mock_post_resp.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_post_resp)

            # GET: 403 에러
            mock_get_resp = MagicMock()
            mock_get_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Forbidden",
                request=httpx.Request("GET", "https://test.com"),
                response=httpx.Response(403, text="Forbidden"),
            )
            mock_client.get = AsyncMock(return_value=mock_get_resp)

            mock_client_cls.return_value = mock_client

            with patch("ai_env.core.research.asyncio.sleep", new_callable=AsyncMock):
                result = await dispatch_openai_deep_research(
                    prompt="test", api_key="bad-key", timeout=60
                )

        assert result.error is not None
        assert "403" in result.error
        # 1회 GET만 호출 (재시도 없이 즉시 실패)
        assert mock_client.get.call_count == 1

    @pytest.mark.asyncio()
    async def test_openai_empty_content(self):
        """콘텐츠 없는 응답"""
        with patch("ai_env.core.research.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)

            mock_resp = MagicMock()
            mock_resp.json.return_value = {"status": "completed", "output": []}
            mock_resp.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_resp)

            mock_client_cls.return_value = mock_client

            result = await dispatch_openai_deep_research(prompt="test", api_key="key")

        assert result.error is not None
        assert "추출 실패" in result.error


# ── 통합 디스패치 테스트 ──


class TestDispatchIntegration:
    @pytest.mark.asyncio()
    async def test_dispatch_with_both_keys(self, sample_topic: TopicConfig, tmp_path: Path):
        """양쪽 API 동시 호출"""
        gemini_result = DeepResearchResult(
            provider="gemini",
            prompt="Gemini 리서치 프롬프트",
            output_path="07_참고/gemini-deep-test.md",
            content="Gemini 결과",
            elapsed_seconds=10.0,
        )
        openai_result = DeepResearchResult(
            provider="openai",
            prompt="GPT 리서치 프롬프트",
            output_path="07_참고/gpt-deep-test.md",
            content="OpenAI 결과",
            elapsed_seconds=15.0,
        )

        with (
            patch(
                "ai_env.core.research.dispatch_gemini_deep_research",
                return_value=gemini_result,
            ),
            patch(
                "ai_env.core.research.dispatch_openai_deep_research",
                return_value=openai_result,
            ),
        ):
            results = await dispatch_deep_research(
                topic=sample_topic,
                obsidian_base=tmp_path,
                google_api_key="goog-key",
                openai_api_key="oai-key",
            )

        assert len(results) == 2
        providers = {r.provider for r in results}
        assert providers == {"gemini", "openai"}

        # 파일 저장 확인
        gemini_file = tmp_path / "07_참고" / "gemini-deep-test.md"
        assert gemini_file.exists()
        content = gemini_file.read_text()
        assert "Gemini Deep Research (API)" in content

    @pytest.mark.asyncio()
    async def test_dispatch_gemini_only(self, sample_topic: TopicConfig, tmp_path: Path):
        """Gemini만 사용 (OpenAI 키 없음)"""
        gemini_result = DeepResearchResult(
            provider="gemini",
            prompt="test",
            output_path="07_참고/gemini-deep-test.md",
            content="결과",
            elapsed_seconds=5.0,
        )

        with patch(
            "ai_env.core.research.dispatch_gemini_deep_research",
            return_value=gemini_result,
        ):
            results = await dispatch_deep_research(
                topic=sample_topic,
                obsidian_base=tmp_path,
                google_api_key="goog-key",
                openai_api_key=None,
            )

        assert len(results) == 1
        assert results[0].provider == "gemini"

    @pytest.mark.asyncio()
    async def test_dispatch_no_keys_returns_empty(self, sample_topic: TopicConfig, tmp_path: Path):
        """키 없으면 빈 리스트 반환"""
        results = await dispatch_deep_research(
            topic=sample_topic,
            obsidian_base=tmp_path,
            google_api_key=None,
            openai_api_key=None,
        )
        assert results == []

    @pytest.mark.asyncio()
    async def test_result_saved_with_frontmatter(self, sample_topic: TopicConfig, tmp_path: Path):
        """결과 파일에 frontmatter 포함"""
        gemini_result = DeepResearchResult(
            provider="gemini",
            prompt="test",
            output_path="07_참고/gemini-deep-test.md",
            content="# 분석 결과\n\n상세 내용",
            sources=["https://src.com"],
            elapsed_seconds=60.0,
        )

        with patch(
            "ai_env.core.research.dispatch_gemini_deep_research",
            return_value=gemini_result,
        ):
            await dispatch_deep_research(
                topic=sample_topic,
                obsidian_base=tmp_path,
                google_api_key="key",
                openai_api_key=None,
            )

        saved = (tmp_path / "07_참고" / "gemini-deep-test.md").read_text()
        assert "---" in saved
        assert "track: B" in saved
        assert "topic: test-topic" in saved
        assert "# 테스트 포커스" in saved
        assert "https://src.com" in saved

    @pytest.mark.asyncio()
    async def test_dispatch_with_research_override(self, sample_topic: TopicConfig, tmp_path: Path):
        """research_override로 프롬프트 매핑 파일 프롬프트 사용"""
        override = ResearchConfig(
            gemini_deep=[
                DeepResearchItem(
                    prompt="매핑 파일 Gemini 프롬프트",
                    output="07_참고/gemini-override.md",
                    focus="오버라이드 포커스",
                ),
            ],
            gpt_deep=[],  # GPT는 비어있음
        )

        gemini_result = DeepResearchResult(
            provider="gemini",
            prompt="매핑 파일 Gemini 프롬프트",
            output_path="07_참고/gemini-override.md",
            content="오버라이드 결과",
            elapsed_seconds=10.0,
        )

        with patch(
            "ai_env.core.research.dispatch_gemini_deep_research",
            return_value=gemini_result,
        ):
            results = await dispatch_deep_research(
                topic=sample_topic,
                obsidian_base=tmp_path,
                google_api_key="goog-key",
                openai_api_key="oai-key",  # GPT 키 있어도 override에 gpt_deep 비어있으면 스킵
                research_override=override,
            )

        # override에 gemini 1건만 있으므로 1건만 반환
        assert len(results) == 1
        assert results[0].provider == "gemini"
        assert results[0].output_path == "07_참고/gemini-override.md"

        # override 파일 경로로 저장 확인
        saved_file = tmp_path / "07_참고" / "gemini-override.md"
        assert saved_file.exists()

    @pytest.mark.asyncio()
    async def test_dispatch_override_ignores_topic_research(
        self, sample_topic: TopicConfig, tmp_path: Path
    ):
        """override가 있으면 topic.research는 무시됨"""
        # topic에는 gemini+gpt 있지만, override에는 빈 설정
        empty_override = ResearchConfig()

        results = await dispatch_deep_research(
            topic=sample_topic,
            obsidian_base=tmp_path,
            google_api_key="goog-key",
            openai_api_key="oai-key",
            research_override=empty_override,
        )

        # override가 비어있으므로 빈 리스트
        assert results == []
