#!/usr/bin/env python3
"""
Tests for generate_draft.py

Usage:
    uv run pytest .claude/skills/jira-weekly-update/scripts/test_generate_draft.py -v
"""

import asyncio
from pathlib import Path
from unittest.mock import Mock

import pytest

# Import the module under test
from generate_draft import (
    ALLOWED_DOMAINS,
    JIRA_API_TOKEN,
    JIRA_PROJECT_KEY,
    JIRA_SERVER_URL,
    PROJECT_ROOT,
    SERVICE_MAPPING,
    SERVICE_ORDER,
    DraftGenerator,
    _convert_confluence_url_to_api,
    # Crawler
    _convert_github_url_to_api,
    # DraftGenerator
    _get_service_from_summary,
    fetch_url_content,
    # Config
    find_project_root,
    get_issues_for_weekly_report,
    # JIRA Client
    get_jira_client,
)

# =============================================================================
# Configuration Tests
# =============================================================================


class TestConfiguration:
    """설정 관련 테스트"""

    def test_find_project_root_returns_path(self):
        """프로젝트 루트가 Path 객체로 반환되어야 함"""
        root = find_project_root()
        assert isinstance(root, Path)
        assert root.exists()
        assert (root / "pyproject.toml").exists()

    def test_project_root_is_valid(self):
        """PROJECT_ROOT가 유효한 경로여야 함"""
        assert PROJECT_ROOT.exists()
        assert (PROJECT_ROOT / "pyproject.toml").exists()

    def test_env_variables_loaded(self):
        """환경변수가 .env에서 로드되어야 함"""
        assert JIRA_SERVER_URL is not None, "JIRA_SERVER_URL not set in .env"
        assert JIRA_PROJECT_KEY is not None, "JIRA_PROJECT_KEY not set in .env"
        assert JIRA_API_TOKEN is not None, "JIRA_API_TOKEN not set in .env"

    def test_service_order_defined(self):
        """서비스 순서가 정의되어야 함"""
        assert len(SERVICE_ORDER) == 5
        assert "선물하기" in SERVICE_ORDER
        assert "톡딜" in SERVICE_ORDER
        assert "쇼핑탭" in SERVICE_ORDER
        assert "라이브" in SERVICE_ORDER
        assert "기타" in SERVICE_ORDER

    def test_service_mapping_defined(self):
        """서비스 매핑이 정의되어야 함"""
        assert "[선물하기]" in SERVICE_MAPPING
        assert "[톡딜]" in SERVICE_MAPPING
        assert "[쇼핑탭]" in SERVICE_MAPPING
        assert "[쇼핑하기]" in SERVICE_MAPPING
        assert "[라이브]" in SERVICE_MAPPING

    def test_allowed_domains(self):
        """허용 도메인이 정의되어야 함"""
        assert "github.daumkakao.com" in ALLOWED_DOMAINS
        assert "wiki.daumkakao.com" in ALLOWED_DOMAINS


# =============================================================================
# JIRA Client Tests
# =============================================================================


class TestJiraClient:
    """JIRA 클라이언트 테스트"""

    def test_get_jira_client_returns_client(self):
        """JIRA 클라이언트가 반환되어야 함"""
        client = get_jira_client()
        assert client is not None

    def test_get_issues_for_weekly_report(self):
        """주간 보고서용 이슈 조회가 동작해야 함"""
        issues = get_issues_for_weekly_report()
        assert isinstance(issues, list)
        # 실제 이슈가 있어야 함 (빈 리스트면 JIRA 설정 확인 필요)
        assert len(issues) > 0, "No issues found - check JIRA configuration"


# =============================================================================
# Crawler Tests - URL Conversion
# =============================================================================


class TestGithubUrlConversion:
    """GitHub URL 변환 테스트"""

    def test_convert_pr_url(self):
        """PR URL이 API URL로 변환되어야 함"""
        url = "https://github.daumkakao.com/KCAI/repo/pull/123"
        api_url = _convert_github_url_to_api(url)
        assert api_url == "https://github.daumkakao.com/api/v3/repos/KCAI/repo/pulls/123"

    def test_convert_issue_url(self):
        """Issue URL이 API URL로 변환되어야 함"""
        url = "https://github.daumkakao.com/KCAI/repo/issues/456"
        api_url = _convert_github_url_to_api(url)
        assert api_url == "https://github.daumkakao.com/api/v3/repos/KCAI/repo/issues/456"

    def test_convert_blob_url(self):
        """Blob URL이 API URL로 변환되어야 함"""
        url = "https://github.daumkakao.com/KCAI/repo/blob/main/src/file.py"
        api_url = _convert_github_url_to_api(url)
        assert (
            api_url
            == "https://github.daumkakao.com/api/v3/repos/KCAI/repo/contents/src/file.py?ref=main"
        )

    def test_convert_tree_url(self):
        """Tree URL이 API URL로 변환되어야 함"""
        url = "https://github.daumkakao.com/KCAI/repo/tree/develop/src/folder"
        api_url = _convert_github_url_to_api(url)
        assert (
            api_url
            == "https://github.daumkakao.com/api/v3/repos/KCAI/repo/contents/src/folder?ref=develop"
        )

    def test_convert_release_url(self):
        """Release URL이 API URL로 변환되어야 함"""
        url = "https://github.daumkakao.com/KCAI/repo/releases/tag/v1.0.0"
        api_url = _convert_github_url_to_api(url)
        assert api_url == "https://github.daumkakao.com/api/v3/repos/KCAI/repo/releases/tags/v1.0.0"

    def test_unconvertible_url_returns_empty(self):
        """변환 불가능한 URL은 빈 문자열 반환"""
        url = "https://github.daumkakao.com/KCAI/repo"
        api_url = _convert_github_url_to_api(url)
        assert api_url == ""


class TestConfluenceUrlConversion:
    """Confluence URL 변환 테스트"""

    def test_convert_page_id_url(self):
        """pageId URL이 API URL로 변환되어야 함"""
        url = "https://wiki.daumkakao.com/pages/viewpage.action?pageId=123456789"
        api_url = _convert_confluence_url_to_api(url)
        assert (
            api_url == "https://wiki.daumkakao.com/rest/api/content/123456789?expand=body.storage"
        )

    def test_convert_pages_path_url(self):
        """/pages/ID/ URL이 API URL로 변환되어야 함"""
        url = "https://wiki.daumkakao.com/spaces/KCAI/pages/123456789/Page+Title"
        api_url = _convert_confluence_url_to_api(url)
        assert (
            api_url == "https://wiki.daumkakao.com/rest/api/content/123456789?expand=body.storage"
        )

    def test_convert_display_url(self):
        """/display/ URL이 API URL로 변환되어야 함"""
        url = "https://wiki.daumkakao.com/display/KCAI/Page+Title"
        api_url = _convert_confluence_url_to_api(url)
        assert "spaceKey=KCAI" in api_url
        assert "title=Page Title" in api_url

    def test_convert_overview_url(self):
        """overview URL이 homepage: prefix로 변환되어야 함"""
        url = "https://wiki.daumkakao.com/spaces/KCAI/overview"
        api_url = _convert_confluence_url_to_api(url)
        assert api_url == "homepage:KCAI"


# =============================================================================
# Crawler Tests - Fetch Content
# =============================================================================


class TestFetchUrlContent:
    """URL 콘텐츠 가져오기 테스트"""

    def test_fetch_disallowed_domain_returns_empty(self):
        """허용되지 않은 도메인은 빈 문자열 반환"""
        url = "https://example.com/some/path"
        content = asyncio.run(fetch_url_content(url))
        assert content == ""

    def test_fetch_github_content(self):
        """GitHub 콘텐츠 가져오기 (토큰 권한 필요)"""
        url = "https://github.daumkakao.com/KCAI/kcai-modeler/pull/195"
        content = asyncio.run(fetch_url_content(url))
        # 토큰이 유효하면 콘텐츠가 있어야 함
        # 현재 토큰 권한 문제로 실패할 수 있음
        assert content != "", "GitHub fetch failed - check GITHUB_TOKEN permission"

    def test_fetch_wiki_content(self):
        """Wiki 콘텐츠 가져오기 (토큰 권한 필요)"""
        url = "https://wiki.daumkakao.com/spaces/KCAI/pages/1892187086/Products+%EC%B6%94%EC%B2%9C"
        content = asyncio.run(fetch_url_content(url))
        # 토큰이 유효하면 콘텐츠가 있어야 함 (403이 아닌)
        # 현재 토큰 권한 문제로 실패할 수 있음
        assert (
            "HTTP error: 403" not in content
        ), "Wiki fetch failed with 403 - check WIKI_TOKEN permission"


# =============================================================================
# Service Classification Tests
# =============================================================================


class TestServiceClassification:
    """서비스 분류 테스트"""

    def test_get_service_gift(self):
        """[선물하기] prefix는 선물하기로 분류"""
        assert _get_service_from_summary("[선물하기] 상품상세 전체 개편") == "선물하기"

    def test_get_service_tokdeal(self):
        """[톡딜] prefix는 톡딜로 분류"""
        assert _get_service_from_summary("[톡딜] 카테고리 매핑 개선") == "톡딜"

    def test_get_service_shopping_tab(self):
        """[쇼핑탭] prefix는 쇼핑탭으로 분류"""
        assert _get_service_from_summary("[쇼핑탭] 최근본 상품 추천") == "쇼핑탭"

    def test_get_service_shopping(self):
        """[쇼핑하기] prefix도 쇼핑탭으로 분류"""
        assert _get_service_from_summary("[쇼핑하기] 킬러카드 추천") == "쇼핑탭"

    def test_get_service_live(self):
        """[라이브] prefix는 라이브로 분류"""
        assert _get_service_from_summary("[라이브] 실시간 추천") == "라이브"

    def test_get_service_common_is_etc(self):
        """[공통] prefix는 기타로 분류"""
        assert _get_service_from_summary("[공통] 공통 모듈 개선") == "기타"

    def test_get_service_unknown_is_etc(self):
        """알 수 없는 prefix는 기타로 분류"""
        assert _get_service_from_summary("기타 업무") == "기타"


# =============================================================================
# DraftGenerator Tests
# =============================================================================


class TestDraftGenerator:
    """DraftGenerator 테스트"""

    def test_group_by_service(self):
        """서비스별 그룹화가 정상 동작해야 함"""
        # Mock issues를 사용하지 않고 메서드만 테스트
        generator = Mock(spec=DraftGenerator)
        generator._group_by_service = DraftGenerator._group_by_service

        component_data = {
            "epics": [
                {
                    "key": "KCAI-1",
                    "summary": "[선물하기] Epic 1",
                    "service": "선물하기",
                    "tasks": [],
                },
                {"key": "KCAI-2", "summary": "[톡딜] Epic 2", "service": "톡딜", "tasks": []},
                {
                    "key": "KCAI-3",
                    "summary": "[선물하기] Epic 3",
                    "service": "선물하기",
                    "tasks": [],
                },
            ]
        }

        result = generator._group_by_service(generator, component_data)

        assert "services" in result
        assert "선물하기" in result["services"]
        assert "톡딜" in result["services"]
        assert len(result["services"]["선물하기"]) == 2
        assert len(result["services"]["톡딜"]) == 1

    def test_group_by_service_order(self):
        """서비스 순서가 SERVICE_ORDER대로 정렬되어야 함"""
        generator = Mock(spec=DraftGenerator)
        generator._group_by_service = DraftGenerator._group_by_service

        component_data = {
            "epics": [
                {"key": "KCAI-1", "summary": "[기타]", "service": "기타", "tasks": []},
                {"key": "KCAI-2", "summary": "[선물하기]", "service": "선물하기", "tasks": []},
                {"key": "KCAI-3", "summary": "[톡딜]", "service": "톡딜", "tasks": []},
            ]
        }

        result = generator._group_by_service(generator, component_data)
        service_keys = list(result["services"].keys())

        # 선물하기 -> 톡딜 -> 기타 순서
        assert service_keys.index("선물하기") < service_keys.index("톡딜")
        assert service_keys.index("톡딜") < service_keys.index("기타")


class TestDraftGeneratorIntegration:
    """DraftGenerator 통합 테스트"""

    def test_generate_draft_data(self):
        """Draft 데이터 생성이 동작해야 함"""
        issues = get_issues_for_weekly_report()
        if not issues:
            pytest.skip("No issues found - skipping integration test")

        generator = DraftGenerator(issues)
        draft_data = asyncio.run(generator.generate_draft_data())

        assert isinstance(draft_data, dict)
        assert len(draft_data) > 0

        # 각 component에 services 키가 있어야 함
        for _component_name, component_data in draft_data.items():
            assert "services" in component_data
            assert isinstance(component_data["services"], dict)

    def test_save_draft(self, tmp_path):
        """Draft 저장이 동작해야 함"""
        issues = get_issues_for_weekly_report()
        if not issues:
            pytest.skip("No issues found - skipping integration test")

        generator = DraftGenerator(issues)
        draft_data = asyncio.run(generator.generate_draft_data())

        output_dir = tmp_path / "test_draft"
        generator.save_draft(draft_data, output_dir)

        # _index.yaml이 생성되어야 함
        assert (output_dir / "_index.yaml").exists()

        # 각 component 파일이 생성되어야 함
        for component_name in draft_data.keys():
            safe_name = component_name.replace("/", "_")
            assert (output_dir / f"{safe_name}.yaml").exists()


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
