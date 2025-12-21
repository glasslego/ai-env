#!/usr/bin/env python3
"""Agit Bot API 클라이언트.

이 모듈은 Agit Bot API v2와 통신하여 그룹, 게시글(wall_messages), 댓글을 조회합니다.
Agit Bot API는 Slack 스타일의 메소드 기반 API입니다.
"""

import os
from pathlib import Path
from typing import Any

import requests

try:
    from dotenv import load_dotenv

    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


def load_agit_token(env_file: str | None = None) -> str:
    """환경변수에서 Agit Bot Token을 로드합니다.

    .env 파일이 있으면 자동으로 로드합니다.

    Args:
        env_file: .env 파일 경로 (선택). 지정하지 않으면 현재 디렉토리에서 찾음

    Returns:
        Agit Bot Token

    Raises:
        ValueError: AGIT_BOT_TOKEN이 설정되지 않은 경우

    Example:
        >>> token = load_agit_token()
        >>> client = AgitClient(token=token)
    """
    # Load .env file if dotenv is available
    if DOTENV_AVAILABLE:
        if env_file:
            load_dotenv(env_file)
        else:
            # Try to find .env in skill directory
            skill_dir = Path(__file__).parent.parent
            env_path = skill_dir / ".env"
            if env_path.exists():
                load_dotenv(env_path)

    # Get token from environment
    token = os.getenv("AGIT_BOT_TOKEN")
    if not token:
        raise ValueError(
            "AGIT_BOT_TOKEN not found. "
            "Set the environment variable or create .env file "
            "in .claude/skills/agit-search/"
        )

    return token


class AgitClient:
    """Agit Bot API v2 클라이언트 클래스."""

    def __init__(
        self, token: str, base_url: str = "https://api.agit.in", timeout: int = 30
    ) -> None:
        """AgitClient를 초기화합니다.

        Args:
            token: Bot access token (Bearer token)
            base_url: Agit API base URL (default: https://api.agit.in)
            timeout: 요청 타임아웃 (초)

        Example:
            >>> token = load_agit_token()
            >>> client = AgitClient(token=token)
        """
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """HTTP 세션을 생성합니다.

        Returns:
            설정된 requests.Session 객체
        """
        session = requests.Session()
        session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
            }
        )
        return session

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """API 요청을 실행합니다.

        Args:
            method: HTTP 메서드 (GET, POST 등)
            endpoint: API 엔드포인트 (/v2/wall_messages 등)
            params: 쿼리 파라미터
            **kwargs: requests 추가 인자

        Returns:
            API 응답 JSON

        Raises:
            requests.HTTPError: HTTP 에러 발생 시
            ValueError: JSON 파싱 실패 시
        """
        url = f"{self.base_url}{endpoint}"

        response = self.session.request(
            method=method, url=url, params=params, timeout=self.timeout, **kwargs
        )

        response.raise_for_status()
        return response.json()

    def get_groups(self, limit: int | None = None) -> list[dict[str, Any]]:
        """접근 가능한 그룹 목록을 조회합니다.

        Args:
            limit: 조회할 그룹 수 (선택)

        Returns:
            그룹 목록

        Example:
            >>> groups = client.get_groups(limit=50)
            >>> for group in groups:
            ...     print(f"{group['id']}: {group.get('name', 'N/A')}")
        """
        endpoint = "/v2/groups"
        params = {}
        if limit:
            params["limit"] = limit

        response = self._make_request("GET", endpoint, params=params)
        return response.get("groups", [])

    def get_wall_messages(
        self,
        group_id: int,
        limit: int = 20,
        oldest: int | None = None,
        latest: int | None = None,
    ) -> list[dict[str, Any]]:
        """그룹의 게시글(wall_messages) 목록을 조회합니다.

        Args:
            group_id: 그룹 ID
            limit: 조회할 게시글 수 (default: 20)
            oldest: 이 ID 이후의 게시글 조회 (pagination)
            latest: 이 ID 이전의 게시글 조회 (pagination)

        Returns:
            게시글 목록

        Example:
            >>> messages = client.get_wall_messages(group_id=300068539, limit=10)
            >>> for msg in messages:
            ...     print(f"{msg['id']}: {msg.get('text', '')[:50]}")
        """
        endpoint = "/v2/wall_messages"
        params = {"group_id": group_id, "limit": limit}

        if oldest is not None:
            params["oldest"] = oldest
        if latest is not None:
            params["latest"] = latest

        response = self._make_request("GET", endpoint, params=params)
        return response.get("wall_messages", [])

    def get_wall_message(self, wall_message_id: int) -> dict[str, Any]:
        """특정 게시글을 조회합니다.

        Args:
            wall_message_id: 게시글 ID

        Returns:
            게시글 정보

        Example:
            >>> message = client.get_wall_message(444958917)
            >>> print(f"Text: {message['text']}")
            >>> print(f"Group: {message['group_id']}")
        """
        endpoint = f"/v2/wall_messages/{wall_message_id}"
        response = self._make_request("GET", endpoint)
        return response.get("wall_message", {})

    def get_wall_message_comments(
        self, wall_message_id: int, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """게시글의 댓글 목록을 조회합니다.

        Args:
            wall_message_id: 게시글 ID
            limit: 조회할 댓글 수 (선택)

        Returns:
            댓글 목록

        Example:
            >>> comments = client.get_wall_message_comments(444958917)
            >>> for comment in comments:
            ...     user = comment.get('user', {})
            ...     print(f"{user.get('name')}: {comment.get('text')}")
        """
        endpoint = f"/v2/wall_messages/{wall_message_id}/comments"
        params = {}
        if limit:
            params["limit"] = limit

        response = self._make_request("GET", endpoint, params=params)
        return response.get("comments", [])

    def get_conversations(self) -> list[dict[str, Any]]:
        """접근 가능한 대화 목록을 조회합니다.

        Returns:
            대화 목록

        Example:
            >>> conversations = client.get_conversations()
            >>> for conv in conversations:
            ...     print(f"{conv['id']}: {conv.get('name', 'N/A')}")
        """
        endpoint = "/v2/conversations.list"
        response = self._make_request("GET", endpoint)
        return response.get("conversations", [])

    def search_wall_messages_by_user(
        self,
        user_email: str = None,
        user_name: str = None,
        ldap_id: str = None,
        max_groups: int = 50,
        messages_per_group: int = 20,
    ) -> list[dict[str, Any]]:
        """사용자의 게시글을 검색합니다.

        Args:
            user_email: 사용자 이메일 (부분 일치)
            user_name: 사용자 이름 (부분 일치)
            ldap_id: LDAP ID (부분 일치)
            max_groups: 검색할 최대 그룹 수 (default: 50)
            messages_per_group: 그룹당 조회할 메시지 수 (default: 20)

        Returns:
            발견된 게시글 목록 (created_time 기준 내림차순 정렬)

        Example:
            >>> posts = client.search_wall_messages_by_user(
            ...     user_email="megan.won@kakao.com"
            ... )
            >>> for post in posts:
            ...     print(f"{post['id']}: {post['text'][:50]}")
        """
        found_messages = []

        # Get groups
        groups = self.get_groups()

        # Search through groups
        for i, group in enumerate(groups[:max_groups]):
            if i > 0 and i % 10 == 0:
                print(f"Searched {i}/{min(max_groups, len(groups))} groups...")

            group_id = group.get("id")

            try:
                messages = self.get_wall_messages(group_id=group_id, limit=messages_per_group)

                for msg in messages:
                    user = msg.get("user", {})
                    msg_user_name = (user.get("name") or "").lower()
                    msg_user_email = (user.get("email") or "").lower()
                    msg_ldap_id = (user.get("ldap_id") or "").lower()

                    # Check if matches search criteria
                    matches = False
                    if user_email and user_email.lower() in msg_user_email:
                        matches = True
                    if user_name and user_name.lower() in msg_user_name:
                        matches = True
                    if ldap_id and ldap_id.lower() in msg_ldap_id:
                        matches = True

                    if matches:
                        found_messages.append(msg)

            except Exception:
                continue

        # Sort by created_time (most recent first)
        found_messages.sort(key=lambda x: x.get("created_time", 0), reverse=True)

        return found_messages


if __name__ == "__main__":
    # Example usage
    token = os.getenv("AGIT_BOT_TOKEN")
    if not token:
        print("Error: AGIT_BOT_TOKEN environment variable is required")
        exit(1)

    client = AgitClient(token=token)

    print("AgitClient initialized successfully")
    print("Available methods:")
    print("  - get_groups(limit)")
    print("  - get_wall_messages(group_id, limit, oldest, latest)")
    print("  - get_wall_message(wall_message_id)")
    print("  - get_wall_message_comments(wall_message_id, limit)")
    print("  - get_conversations()")
    print("  - search_wall_messages_by_user(user_email, user_name, ldap_id)")
