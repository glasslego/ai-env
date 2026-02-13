#!/usr/bin/env python3
"""
Weekly Report Draft Generator for Claude Code Skill

JIRA 이슈를 조회하여 Component별 YAML 파일로 분할 생성합니다.
각 파일 내에서 서비스(선물하기, 톡딜, 쇼핑탭, 라이브, 기타)별로 그룹화됩니다.

이 스크립트는 독립 실행 가능하며, src/ 모듈에 의존하지 않습니다.
환경변수는 레포 루트의 .env 파일에서 로드합니다.

Usage:
    uv run python .claude/skills/jira-weekly-update/scripts/generate_draft.py

Output:
    reports/draft/draft_weekly_YYYYMMDD/
    ├── _index.yaml      # Component 목록
    ├── 추천.yaml
    ├── 타겟팅.yaml
    └── ...
"""

import asyncio
import base64
import json
import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import yaml
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from jira import JIRA
from jira.resources import Issue

# =============================================================================
# 1. Configuration
# =============================================================================


def find_project_root() -> Path:
    """pyproject.toml 기준으로 프로젝트 루트를 탐지합니다."""
    current = Path(__file__).resolve().parent
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError("Cannot find project root (pyproject.toml not found)")


PROJECT_ROOT = find_project_root()

# .env 파일 로드
load_dotenv(PROJECT_ROOT / ".env")

# JIRA 설정
JIRA_SERVER_URL = os.environ.get("JIRA_SERVER_URL")
JIRA_PROJECT_KEY = os.environ.get("JIRA_PROJECT_KEY")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN")
EPIC_LINK_FIELD_ID = "customfield_10350"

# Crawler 설정
WIKI_TOKEN = os.environ.get("WIKI_TOKEN")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
ALLOWED_DOMAINS = ["github.daumkakao.com", "wiki.daumkakao.com"]

# 서비스 분류 순서
SERVICE_ORDER = ["선물하기", "톡딜", "쇼핑탭", "라이브", "기타"]

# 서비스 매핑 (Epic summary prefix -> 서비스명)
SERVICE_MAPPING = {
    "[선물하기]": "선물하기",
    "[톡딜]": "톡딜",
    "[쇼핑탭]": "쇼핑탭",
    "[쇼핑하기]": "쇼핑탭",
    "[라이브]": "라이브",
}

# URL 추출용 정규식
URL_REGEX = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"


# =============================================================================
# 2. JIRA Client
# =============================================================================


def get_jira_client() -> JIRA:
    """JIRA 클라이언트를 초기화하고 반환합니다."""
    if not JIRA_SERVER_URL or not JIRA_API_TOKEN:
        raise ValueError("JIRA_SERVER_URL and JIRA_API_TOKEN must be set in .env")

    return JIRA(
        options={"server": JIRA_SERVER_URL},
        token_auth=JIRA_API_TOKEN,
    )


def get_issues_for_weekly_report() -> list[Issue]:
    """주간 보고서용 이슈를 조회합니다."""
    jira = get_jira_client()

    jql_query = (
        f'project = "{JIRA_PROJECT_KEY}" AND '
        'issuetype = "Task" AND '
        '(status = "Closed" OR status = "In Progress") AND '
        "fixVersion is EMPTY "
        "ORDER BY Rank ASC"
    )

    required_fields = [
        "summary",
        "status",
        "components",
        "assignee",
        "comment",
        "description",
        EPIC_LINK_FIELD_ID,
    ]

    issues = jira.search_issues(jql_query, maxResults=100, fields=required_fields)
    return issues


# =============================================================================
# 3. Crawler
# =============================================================================


def _convert_github_url_to_api(url: str) -> str:
    """GitHub 웹 URL을 API URL로 변환합니다."""
    # PR: /org/repo/pull/123
    pr_match = re.match(r"https?://github\.daumkakao\.com/([^/]+)/([^/]+)/pull/(\d+)", url)
    if pr_match:
        org, repo, pr_number = pr_match.groups()
        return f"https://github.daumkakao.com/api/v3/repos/{org}/{repo}/pulls/{pr_number}"

    # Issue: /org/repo/issues/123
    issue_match = re.match(r"https?://github\.daumkakao\.com/([^/]+)/([^/]+)/issues/(\d+)", url)
    if issue_match:
        org, repo, issue_number = issue_match.groups()
        return f"https://github.daumkakao.com/api/v3/repos/{org}/{repo}/issues/{issue_number}"

    # File or Directory: /org/repo/tree/branch/path or /org/repo/blob/branch/path
    content_match = re.match(
        r"https?://github\.daumkakao\.com/([^/]+)/([^/]+)/(?:tree|blob)/([^/]+)/(.+)", url
    )
    if content_match:
        org, repo, branch, path = content_match.groups()
        return (
            f"https://github.daumkakao.com/api/v3/repos/{org}/{repo}/contents/{path}?ref={branch}"
        )

    # Release: /org/repo/releases/tag/v1.0.0
    release_match = re.match(
        r"https?://github\.daumkakao\.com/([^/]+)/([^/]+)/releases/tag/([^/]+)", url
    )
    if release_match:
        org, repo, tag = release_match.groups()
        return f"https://github.daumkakao.com/api/v3/repos/{org}/{repo}/releases/tags/{tag}"

    return ""


def _convert_confluence_url_to_api(url: str) -> str:
    """Confluence 웹 URL을 API URL로 변환합니다."""
    # Overview page
    overview_match = re.search(r"/(?:spaces|display)/([^/]+)/overview", url)
    if overview_match:
        space_key = overview_match.group(1)
        return f"homepage:{space_key}"

    # pageId parameter
    page_id_match = re.search(r"pageId=(\d+)", url)
    if page_id_match:
        page_id = page_id_match.group(1)
        return f"https://wiki.daumkakao.com/rest/api/content/{page_id}?expand=body.storage"

    # /pages/viewpage.action?pageId=...
    page_id_from_path_match = re.search(r"/pages/viewpage\.action\?pageId=(\d+)", url)
    if page_id_from_path_match:
        page_id = page_id_from_path_match.group(1)
        return f"https://wiki.daumkakao.com/rest/api/content/{page_id}?expand=body.storage"

    # /pages/PAGE_ID/Page+Title format
    page_id_from_path = re.search(r"/pages/(\d+)/", url)
    if page_id_from_path:
        page_id = page_id_from_path.group(1)
        return f"https://wiki.daumkakao.com/rest/api/content/{page_id}?expand=body.storage"

    # /display/SPACE/Page+Title
    display_match = re.search(r"/display/([^/]+)/([^/]+)", url)
    if display_match:
        space_key = display_match.group(1)
        title = display_match.group(2).replace("+", " ")
        return f"https://wiki.daumkakao.com/rest/api/content?spaceKey={space_key}&title={title}&expand=body.storage"

    return ""


async def fetch_url_content(url: str) -> str:
    """URL의 텍스트 내용을 가져옵니다. GitHub/Wiki는 API를 사용합니다."""
    try:
        parsed_url = urlparse(url)
        if parsed_url.netloc not in ALLOWED_DOMAINS:
            return ""

        headers = {}
        api_url = url
        is_github_api = False

        if parsed_url.netloc == "wiki.daumkakao.com":
            api_url = _convert_confluence_url_to_api(url)
            if not api_url:
                return "Could not convert Confluence URL to API format."
            if WIKI_TOKEN:
                headers["Authorization"] = f"Bearer {WIKI_TOKEN}"

        elif parsed_url.netloc == "github.daumkakao.com" and GITHUB_TOKEN:
            converted_url = _convert_github_url_to_api(url)
            if converted_url:
                api_url = converted_url
                is_github_api = True
            headers["Authorization"] = f"token {GITHUB_TOKEN}"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                api_url, headers=headers, follow_redirects=True, timeout=10.0
            )
            response.raise_for_status()

            if parsed_url.netloc == "github.daumkakao.com" and is_github_api:
                try:
                    data = response.json()
                    if isinstance(data, list):  # Directory content
                        files = [item["name"] for item in data]
                        return "Directory listing:\n- " + "\n- ".join(files)
                    elif data.get("content"):  # File content
                        decoded_content = base64.b64decode(data["content"]).decode("utf-8")
                        return f"File: {data.get('name')}\n\n{decoded_content}"
                    else:  # PR/Issue/Release
                        title = data.get("title", data.get("name", ""))
                        body = data.get("body", "")
                        return f"Title: {title}\n\nBody:\n{body}"
                except json.JSONDecodeError:
                    return "Failed to decode JSON from GitHub API response."

            else:  # Confluence
                final_api_url = api_url
                if api_url.startswith("homepage:"):
                    space_key = api_url.split(":")[1]
                    space_lookup_url = (
                        f"https://wiki.daumkakao.com/rest/api/space/{space_key}?expand=homepage"
                    )
                    space_response = await client.get(
                        space_lookup_url, headers=headers, follow_redirects=True, timeout=10.0
                    )
                    if space_response.status_code == 403:
                        return f"Permission denied for Confluence space: {space_key}"
                    space_response.raise_for_status()
                    space_data = space_response.json()
                    homepage_id = space_data.get("homepage", {}).get("id")
                    if not homepage_id:
                        return f"Could not find homepage ID for space: {space_key}"
                    final_api_url = f"https://wiki.daumkakao.com/rest/api/content/{homepage_id}?expand=body.storage"

                response = await client.get(
                    final_api_url, headers=headers, follow_redirects=True, timeout=10.0
                )
                if response.status_code == 403:
                    return "Authentication successful, but you do not have permission to view this page."
                response.raise_for_status()

                data = response.json()

                if isinstance(data, list):
                    return "Unexpected response from Confluence API (list of results)."

                title = data.get("title", "")
                body_html = data.get("body", {}).get("storage", {}).get("value", "")

                soup = BeautifulSoup(body_html, "html.parser")
                body_text = soup.get_text(separator="\n", strip=True)

                return f"Title: {title}\n\nBody:\n{body_text}"

    except httpx.HTTPStatusError as e:
        print(
            f"HTTP error for {e.request.url!r}: {e.response.status_code} {e.response.reason_phrase}"
        )
        return f"HTTP error: {e.response.status_code}"
    except httpx.RequestError as e:
        print(f"An error occurred while requesting {e.request.url!r}: {e}")
        return ""
    except Exception as e:
        print(f"An unexpected error occurred for url {url}: {e}")
        return ""


# =============================================================================
# 4. DraftGenerator
# =============================================================================


def _get_service_from_summary(summary: str) -> str:
    """Epic summary에서 서비스명을 추출합니다."""
    for prefix, service in SERVICE_MAPPING.items():
        if summary.startswith(prefix):
            return service
    return "기타"


class DraftGenerator:
    """
    JIRA 이슈를 YAML 형식으로 Draft 생성합니다.
    Component별 분할 파일 생성 및 서비스별 그룹화를 지원합니다.
    """

    def __init__(self, issues: list[Issue]):
        self.jira = get_jira_client()
        self.issues = issues
        self.epic_cache: dict[str, Issue | None] = {}

    def _get_epic(self, epic_key: str) -> Issue | None:
        """Epic 이슈를 가져오고 캐시합니다."""
        if epic_key not in self.epic_cache:
            try:
                self.epic_cache[epic_key] = self.jira.issue(epic_key, fields="summary,components")
            except Exception as e:
                print(f"Could not fetch epic {epic_key}: {e}")
                self.epic_cache[epic_key] = None
        return self.epic_cache[epic_key]

    async def _extract_details_with_crawl(self, text: str) -> dict[str, Any]:
        """텍스트에서 URL을 추출하고 크롤링합니다."""
        if not text:
            return {"text": "", "crawled_content": {}}

        urls = re.findall(URL_REGEX, text)
        cleaned_urls = [url.rstrip(".,;]") for url in urls]

        crawled_content = {}
        if cleaned_urls:
            crawl_tasks = [fetch_url_content(url) for url in cleaned_urls]
            contents = await asyncio.gather(*crawl_tasks)
            for url, content in zip(cleaned_urls, contents, strict=False):
                if content:
                    crawled_content[url] = content[:1000]

        return {"text": text, "crawled_content": crawled_content}

    async def _get_task_details(self, task: Issue) -> dict:
        """단일 Task의 상세 정보를 구성합니다."""
        description_details = await self._extract_details_with_crawl(task.fields.description)

        comments_details = []
        for comment in task.fields.comment.comments:
            comment_content = await self._extract_details_with_crawl(comment.body)
            comments_details.append(
                {
                    "author": comment.author.displayName,
                    "created": comment.created,
                    "body": comment_content["text"],
                    "crawled_content": comment_content["crawled_content"],
                }
            )

        assignee = task.fields.assignee

        return {
            "summary": task.fields.summary,
            "status": task.fields.status.name,
            "key": task.key,
            "url": f"{self.jira.server_info()['baseUrl']}/browse/{task.key}",
            "assignee": assignee.displayName if assignee else "Unassigned",
            "description": description_details,
            "comments": comments_details,
        }

    async def generate_draft_data(self) -> dict:
        """
        이슈를 그룹화하여 구조화된 딕셔너리를 생성합니다.
        Component > Service > Epic > Task 구조로 반환합니다.
        """
        draft_data = defaultdict(lambda: {"epics": []})

        for issue in self.issues:
            epic_key = getattr(issue.fields, EPIC_LINK_FIELD_ID, None)

            if not epic_key:
                component_name = "Uncategorized"
                epic_summary = "Others"
            else:
                epic_issue = self._get_epic(epic_key)
                if epic_issue and epic_issue.fields.components:
                    component_name = epic_issue.fields.components[0].name
                else:
                    component_name = "Uncategorized"

                epic_summary = epic_issue.fields.summary if epic_issue else epic_key

            task_details = await self._get_task_details(issue)

            # Epic이 이미 존재하면 Task 추가
            epic_found = False
            for epic in draft_data[component_name]["epics"]:
                if epic["key"] == epic_key:
                    epic["tasks"].append(task_details)
                    epic_found = True
                    break

            if not epic_found:
                service = _get_service_from_summary(epic_summary)
                draft_data[component_name]["epics"].append(
                    {
                        "key": epic_key or "Others",
                        "summary": epic_summary,
                        "service": service,
                        "url": f"{self.jira.server_info()['baseUrl']}/browse/{epic_key}"
                        if epic_key
                        else "",
                        "tasks": [task_details],
                    }
                )

        # 서비스별 정렬
        def get_service_sort_key(epic):
            service = epic.get("service", "기타")
            try:
                return (SERVICE_ORDER.index(service), epic["summary"])
            except ValueError:
                return (len(SERVICE_ORDER), epic["summary"])

        for component in draft_data:
            draft_data[component]["epics"].sort(key=get_service_sort_key)

        # Component 정렬
        sorted_draft_data = {}
        component_order = ["추천", "타겟팅", "유저/아이템 프로파일링", "운영", "기타"]

        for component_name in component_order:
            if component_name in draft_data:
                sorted_draft_data[component_name] = self._group_by_service(
                    draft_data[component_name]
                )

        for component_name, data in draft_data.items():
            if component_name not in sorted_draft_data:
                sorted_draft_data[component_name] = self._group_by_service(data)

        return sorted_draft_data

    def _get_task_status_priority(self, status: str) -> int:
        """Task 상태의 정렬 우선순위를 반환합니다. (낮을수록 위쪽)"""
        if status in ("Closed", "Resolved"):
            return 0  # 완료 먼저
        return 1  # In Progress 등

    def _group_by_service(self, component_data: dict) -> dict:
        """Epic 목록을 서비스별로 그룹화합니다."""
        services = defaultdict(list)

        for epic in component_data["epics"]:
            service = epic.get("service", "기타")
            epic_copy = {k: v for k, v in epic.items() if k != "service"}

            # Task를 상태별로 정렬 (In Progress 먼저, Closed 나중에)
            if "tasks" in epic_copy:
                epic_copy["tasks"] = sorted(
                    epic_copy["tasks"],
                    key=lambda t: self._get_task_status_priority(t.get("status", "")),
                )

            services[service].append(epic_copy)

        sorted_services = {}
        for service in SERVICE_ORDER:
            if service in services:
                sorted_services[service] = services[service]

        for service, epics in services.items():
            if service not in sorted_services:
                sorted_services[service] = epics

        return {"services": sorted_services}

    def save_draft(self, data: dict, output_dir: Path) -> None:
        """Draft 데이터를 Component별 YAML 파일로 분할 저장합니다."""
        output_dir.mkdir(exist_ok=True, parents=True)

        # _index.yaml 생성
        index_data = {
            "components": list(data.keys()),
            "generated_at": datetime.now().isoformat(),
        }
        index_path = output_dir / "_index.yaml"
        with open(index_path, "w", encoding="utf-8") as f:
            yaml.dump(index_data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        print(f"Index saved to {index_path}")

        # Component별 YAML 파일 생성
        for component_name, component_data in data.items():
            safe_name = component_name.replace("/", "_")
            component_path = output_dir / f"{safe_name}.yaml"

            with open(component_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    {"component": component_name, **component_data},
                    f,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False,
                    width=1000,
                )
            print(f"Component saved to {component_path}")


# =============================================================================
# 5. Main
# =============================================================================


async def main():
    """Component별 YAML 파일을 생성합니다."""
    try:
        issues = get_issues_for_weekly_report()
        if not issues:
            print("No issues found to generate a draft.")
            return

        generator = DraftGenerator(issues)
        draft_data = await generator.generate_draft_data()

        today = datetime.now().strftime("%Y%m%d")
        output_dir = PROJECT_ROOT / "reports" / "draft" / f"draft_weekly_{today}"

        generator.save_draft(draft_data, output_dir)
        print(f"Draft generated successfully: {output_dir}")

    except Exception as e:
        print(f"Error generating draft: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
