"""Deep Research API 디스패치 모듈

Gemini Deep Research API와 OpenAI Deep Research API를 httpx로 호출하여
Track B/C 심층리서치를 자동화한다.

사용법:
    results = await dispatch_deep_research(
        topic=topic,
        obsidian_base=obsidian_base,
        google_api_key="...",
        openai_api_key="...",
    )
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field

from .pipeline import DeepResearchItem, ResearchConfig, TopicConfig

# ── 상수 ──

GEMINI_INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
GEMINI_DEEP_RESEARCH_MODEL = "deep-research-pro-preview-12-2025"

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OPENAI_DEEP_RESEARCH_MODEL = "o4-mini-deep-research"

DEFAULT_POLL_INTERVAL = 15  # 초
DEFAULT_TIMEOUT = 1200  # 20분


# ── Pydantic 결과 모델 ──


class DeepResearchResult(BaseModel):
    """심층리서치 API 호출 결과"""

    provider: str  # "gemini" | "openai"
    prompt: str
    output_path: str
    content: str | None = None  # 성공 시 결과 텍스트
    error: str | None = None  # 실패 시 에러 메시지
    sources: list[str] = Field(default_factory=list)  # 참고 URL
    elapsed_seconds: float = 0.0


# ── Gemini Deep Research ──


async def dispatch_gemini_deep_research(
    prompt: str,
    api_key: str,
    poll_interval: int = DEFAULT_POLL_INTERVAL,
    timeout: int = DEFAULT_TIMEOUT,
) -> DeepResearchResult:
    """Gemini Deep Research API 호출 (Interactions API)

    POST로 리서치 시작 → interaction_id로 polling → 완료 시 결과 반환.

    Args:
        prompt: 리서치 프롬프트
        api_key: Google API 키 (GOOGLE_API_KEY)
        poll_interval: 폴링 간격 (초)
        timeout: 최대 대기 시간 (초)

    Returns:
        DeepResearchResult (content 또는 error 포함)
    """
    start_time = time.monotonic()
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "input": prompt,
        "agent": GEMINI_DEEP_RESEARCH_MODEL,
        "background": True,
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        # 1. 리서치 시작
        try:
            resp = await client.post(GEMINI_INTERACTIONS_URL, json=payload, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            return DeepResearchResult(
                provider="gemini",
                prompt=prompt,
                output_path="",
                error=f"Gemini API 에러 (HTTP {e.response.status_code}): {e.response.text[:500]}",
                elapsed_seconds=time.monotonic() - start_time,
            )
        except httpx.RequestError as e:
            return DeepResearchResult(
                provider="gemini",
                prompt=prompt,
                output_path="",
                error=f"Gemini 요청 실패: {e}",
                elapsed_seconds=time.monotonic() - start_time,
            )

        data = resp.json()
        interaction_id = data.get("id")
        if not interaction_id:
            return DeepResearchResult(
                provider="gemini",
                prompt=prompt,
                output_path="",
                error=f"Gemini 응답에 interaction ID 없음: {data}",
                elapsed_seconds=time.monotonic() - start_time,
            )

        # 2. Polling
        poll_url = f"{GEMINI_INTERACTIONS_URL}/{interaction_id}"
        deadline = start_time + timeout

        while time.monotonic() < deadline:
            await asyncio.sleep(poll_interval)

            try:
                poll_resp = await client.get(poll_url, headers=headers)
                poll_resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                # 4xx 에러(인증/권한/Not Found 등)는 재시도해도 해결 불가
                if 400 <= e.response.status_code < 500:
                    return DeepResearchResult(
                        provider="gemini",
                        prompt=prompt,
                        output_path="",
                        error=f"Gemini polling 에러 (HTTP {e.response.status_code}): {e.response.text[:500]}",
                        elapsed_seconds=time.monotonic() - start_time,
                    )
                continue  # 5xx 등 일시적 에러 시 재시도
            except httpx.RequestError:
                continue  # 네트워크 에러 시 재시도

            poll_data = poll_resp.json()
            state = poll_data.get("state", "")

            if state == "COMPLETED":
                content = _extract_gemini_content(poll_data)
                sources = _extract_gemini_sources(poll_data)
                return DeepResearchResult(
                    provider="gemini",
                    prompt=prompt,
                    output_path="",
                    content=content,
                    sources=sources,
                    elapsed_seconds=time.monotonic() - start_time,
                )

            if state in ("FAILED", "CANCELLED"):
                return DeepResearchResult(
                    provider="gemini",
                    prompt=prompt,
                    output_path="",
                    error=f"Gemini 리서치 {state}: {poll_data}",
                    elapsed_seconds=time.monotonic() - start_time,
                )

            # ACTIVE 상태 → 계속 polling

    return DeepResearchResult(
        provider="gemini",
        prompt=prompt,
        output_path="",
        error=f"Gemini 타임아웃 ({timeout}초)",
        elapsed_seconds=time.monotonic() - start_time,
    )


def _extract_gemini_content(data: dict[str, Any]) -> str:
    """Gemini Interactions API 응답에서 텍스트 추출"""
    # output.content.parts[].text 경로
    output = data.get("output", {})
    if isinstance(output, dict):
        content = output.get("content", {})
        parts = content.get("parts", [])
        texts = [p.get("text", "") for p in parts if isinstance(p, dict)]
        if texts:
            return "\n\n".join(t for t in texts if t)

    # 대체 경로: response.text
    response = data.get("response", {})
    if isinstance(response, dict):
        text = response.get("text", "")
        if text:
            return str(text)

    # candidates 경로 (generateContent 호환)
    candidates = data.get("candidates", [])
    if candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        texts = [p.get("text", "") for p in parts if isinstance(p, dict)]
        if texts:
            return "\n\n".join(t for t in texts if t)

    return str(data)


def _extract_gemini_sources(data: dict[str, Any]) -> list[str]:
    """Gemini 응답에서 참고 URL 추출"""
    sources: list[str] = []

    # groundingMetadata 경로
    candidates = data.get("candidates", [])
    if candidates:
        metadata = candidates[0].get("groundingMetadata", {})
        chunks = metadata.get("groundingChunks", [])
        for chunk in chunks:
            web = chunk.get("web", {})
            uri = web.get("uri", "")
            if uri:
                sources.append(uri)

    # output.sources 경로 (Interactions API)
    output = data.get("output", {})
    if isinstance(output, dict):
        for src in output.get("sources", []):
            if isinstance(src, dict):
                uri = src.get("uri", "") or src.get("url", "")
                if uri:
                    sources.append(uri)

    return sources


# ── OpenAI Deep Research ──


async def dispatch_openai_deep_research(
    prompt: str,
    api_key: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> DeepResearchResult:
    """OpenAI Deep Research API 호출 (Responses API)

    Args:
        prompt: 리서치 프롬프트
        api_key: OpenAI API 키 (OPENAI_API_KEY)
        timeout: 최대 대기 시간 (초)

    Returns:
        DeepResearchResult (content 또는 error 포함)
    """
    start_time = time.monotonic()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_DEEP_RESEARCH_MODEL,
        "input": [{"type": "text", "text": prompt}],
        "tools": [{"type": "web_search_preview"}],
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(float(timeout), connect=30.0)) as client:
        try:
            resp = await client.post(OPENAI_RESPONSES_URL, json=payload, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            return DeepResearchResult(
                provider="openai",
                prompt=prompt,
                output_path="",
                error=f"OpenAI API 에러 (HTTP {e.response.status_code}): {e.response.text[:500]}",
                elapsed_seconds=time.monotonic() - start_time,
            )
        except httpx.RequestError as e:
            return DeepResearchResult(
                provider="openai",
                prompt=prompt,
                output_path="",
                error=f"OpenAI 요청 실패: {e}",
                elapsed_seconds=time.monotonic() - start_time,
            )

        data = resp.json()
        status = data.get("status", "")

        # background mode: incomplete → polling
        if status == "incomplete":
            response_id = data.get("id", "")
            if response_id:
                return await _poll_openai_response(
                    client, response_id, api_key, prompt, start_time, timeout
                )

        content = _extract_openai_content(data)
        sources = _extract_openai_sources(data)

        if content:
            return DeepResearchResult(
                provider="openai",
                prompt=prompt,
                output_path="",
                content=content,
                sources=sources,
                elapsed_seconds=time.monotonic() - start_time,
            )

        return DeepResearchResult(
            provider="openai",
            prompt=prompt,
            output_path="",
            error=f"OpenAI 응답에서 콘텐츠 추출 실패: {data}",
            elapsed_seconds=time.monotonic() - start_time,
        )


async def _poll_openai_response(
    client: httpx.AsyncClient,
    response_id: str,
    api_key: str,
    prompt: str,
    start_time: float,
    timeout: int,
) -> DeepResearchResult:
    """OpenAI incomplete 응답을 polling"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    poll_url = f"{OPENAI_RESPONSES_URL}/{response_id}"
    deadline = start_time + timeout

    while time.monotonic() < deadline:
        await asyncio.sleep(DEFAULT_POLL_INTERVAL)

        try:
            resp = await client.get(poll_url, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            # 4xx 에러(인증/권한/Not Found 등)는 재시도해도 해결 불가
            if 400 <= e.response.status_code < 500:
                return DeepResearchResult(
                    provider="openai",
                    prompt=prompt,
                    output_path="",
                    error=f"OpenAI polling 에러 (HTTP {e.response.status_code}): {e.response.text[:500]}",
                    elapsed_seconds=time.monotonic() - start_time,
                )
            continue  # 5xx 등 일시적 에러 시 재시도
        except httpx.RequestError:
            continue  # 네트워크 에러 시 재시도

        data = resp.json()
        status = data.get("status", "")

        if status == "completed":
            content = _extract_openai_content(data)
            sources = _extract_openai_sources(data)
            return DeepResearchResult(
                provider="openai",
                prompt=prompt,
                output_path="",
                content=content,
                sources=sources,
                elapsed_seconds=time.monotonic() - start_time,
            )

        if status in ("failed", "cancelled"):
            return DeepResearchResult(
                provider="openai",
                prompt=prompt,
                output_path="",
                error=f"OpenAI 리서치 {status}: {data}",
                elapsed_seconds=time.monotonic() - start_time,
            )

    return DeepResearchResult(
        provider="openai",
        prompt=prompt,
        output_path="",
        error=f"OpenAI 타임아웃 ({timeout}초)",
        elapsed_seconds=time.monotonic() - start_time,
    )


def _extract_openai_content(data: dict[str, Any]) -> str:
    """OpenAI Responses API 응답에서 텍스트 추출"""
    # output[].type == "message" → content[].text
    for item in data.get("output", []):
        if not isinstance(item, dict):
            continue
        if item.get("type") == "message":
            for content in item.get("content", []):
                if isinstance(content, dict) and content.get("type") == "output_text":
                    text = content.get("text", "")
                    if text:
                        return str(text)

    # 단순 text 필드
    text = data.get("text", "")
    if text:
        return str(text)

    return ""


def _extract_openai_sources(data: dict[str, Any]) -> list[str]:
    """OpenAI 응답에서 참고 URL 추출"""
    sources: list[str] = []
    for item in data.get("output", []):
        if not isinstance(item, dict):
            continue
        # web_search_call 결과에서 URL 추출
        if item.get("type") == "web_search_call":
            url = item.get("url", "")
            if url:
                sources.append(url)
    return sources


# ── 결과 포맷팅 ──


def format_result_markdown(
    result: DeepResearchResult,
    topic_id: str,
    focus: str | None = None,
) -> str:
    """API 결과를 Obsidian 마크다운으로 포맷

    Args:
        result: API 호출 결과
        topic_id: 토픽 ID
        focus: 조사 초점 (optional)

    Returns:
        frontmatter + 본문 포함 마크다운 문자열
    """
    today = datetime.now().strftime("%Y-%m-%d")
    provider_label = "Gemini Deep Research" if result.provider == "gemini" else "GPT Deep Research"
    track = "B" if result.provider == "gemini" else "C"

    lines = [
        "---",
        f"source: {provider_label} (API)",
        f"date: {today}",
        f"track: {track}",
        f"topic: {topic_id}",
        f"elapsed: {result.elapsed_seconds:.0f}s",
        "---",
        "",
    ]

    if focus:
        lines.append(f"# {focus}")
    else:
        lines.append(f"# {provider_label} 리서치 결과")
    lines.append("")

    if result.content:
        lines.append(result.content)
    else:
        lines.append(f"> API 에러: {result.error}")

    if result.sources:
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## 참고 소스")
        lines.append("")
        for src in result.sources:
            lines.append(f"- {src}")

    lines.append("")
    return "\n".join(lines)


# ── 통합 디스패치 ──


async def dispatch_deep_research(
    topic: TopicConfig,
    obsidian_base: Path,
    google_api_key: str | None = None,
    openai_api_key: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    research_override: ResearchConfig | None = None,
) -> list[DeepResearchResult]:
    """토픽 YAML 기반 Track B/C 심층리서치 디스패치

    Gemini/OpenAI Deep Research API를 병렬 호출하고
    결과를 Obsidian에 마크다운으로 저장한다.

    Args:
        topic: 로드된 토픽 설정
        obsidian_base: Obsidian 토픽 기본 경로
        google_api_key: Google API 키 (없으면 Track B 스킵)
        openai_api_key: OpenAI API 키 (없으면 Track C 스킵)
        timeout: API 타임아웃 (초)
        research_override: 프롬프트 매핑 파일에서 로드한 설정 (None이면 topic.research 사용)

    Returns:
        DeepResearchResult 리스트
    """
    research = research_override if research_override is not None else topic.research
    tasks: list[tuple[DeepResearchItem, str, str]] = []  # (item, provider, api_key)

    # Track B: Gemini
    if google_api_key:
        for item in research.gemini_deep:
            tasks.append((item, "gemini", google_api_key))

    # Track C: OpenAI
    if openai_api_key:
        for item in research.gpt_deep:
            tasks.append((item, "openai", openai_api_key))

    if not tasks:
        return []

    # 병렬 호출
    async def _run_one(item: DeepResearchItem, provider: str, key: str) -> DeepResearchResult:
        if provider == "gemini":
            result = await dispatch_gemini_deep_research(
                prompt=item.prompt, api_key=key, timeout=timeout
            )
        else:
            result = await dispatch_openai_deep_research(
                prompt=item.prompt, api_key=key, timeout=timeout
            )
        result.output_path = item.output

        # 성공 시 파일 저장
        if result.content:
            out_path = obsidian_base / item.output
            out_path.parent.mkdir(parents=True, exist_ok=True)
            md = format_result_markdown(
                result,
                topic_id=topic.topic.id,
                focus=item.focus,
            )
            out_path.write_text(md, encoding="utf-8")

        return result

    coros = [_run_one(item, provider, key) for item, provider, key in tasks]
    results = await asyncio.gather(*coros)
    return list(results)
