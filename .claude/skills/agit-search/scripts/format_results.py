#!/usr/bin/env python3
"""Agit API 결과 포맷팅 유틸리티.

이 모듈은 Agit API 응답을 사람이 읽기 쉬운 형태로 포맷팅합니다.
"""

import json
from datetime import datetime
from typing import Any

# Constants
SEPARATOR_WIDTH = 100
SEPARATOR_LINE = "=" * SEPARATOR_WIDTH
DASH_LINE = "-" * SEPARATOR_WIDTH


def _print_header(title: str) -> None:
    """헤더를 출력합니다.

    Args:
        title: 헤더 제목
    """
    print(f"\n{SEPARATOR_LINE}")
    print(title)
    print(SEPARATOR_LINE)


def _format_timestamp(timestamp: Any) -> str:
    """타임스탬프를 포맷팅합니다.

    Args:
        timestamp: Unix timestamp (밀리초) 또는 문자열

    Returns:
        포맷팅된 날짜 문자열
    """
    if not timestamp:
        return "N/A"
    try:
        if isinstance(timestamp, int | float):
            dt = datetime.fromtimestamp(timestamp / 1000)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        return str(timestamp)
    except (ValueError, OSError):
        return str(timestamp)


def format_post(post: dict[str, Any], verbose: bool = False) -> None:
    """게시글 정보를 포맷팅합니다.

    Args:
        post: 게시글 데이터
        verbose: 상세 모드 (전체 데이터 출력)

    Example:
        >>> post = client.get_post(12345)
        >>> format_post(post)
    """
    _print_header(f"Post: {post.get('id', 'N/A')}")

    author_name = post.get("authorName", "N/A")
    author_id = post.get("authorId", "N/A")
    group_name = post.get("groupName", "N/A")
    group_id = post.get("groupId", "N/A")

    print(f"Title:        {post.get('title', 'N/A')}")
    print(f"Author:       {author_name} (ID: {author_id})")
    print(f"Group:        {group_name} (ID: {group_id})")
    print(f"Created:      {_format_timestamp(post.get('createdAt'))}")
    print(f"Updated:      {_format_timestamp(post.get('updatedAt'))}")
    print(f"Comments:     {post.get('commentCount', 0)}")
    print(f"Reactions:    {post.get('reactionCount', 0)}")

    content = post.get("content", {})
    if content:
        print("\nContent:")
        print(f"  Type:       {content.get('type', 'N/A')}")
        print(f"  Text:       {content.get('text', 'N/A')[:200]}...")

    if verbose:
        print(f"\n{DASH_LINE}")
        print("Full Data:")
        print(DASH_LINE)
        print(json.dumps(post, indent=2, ensure_ascii=False))

    print(SEPARATOR_LINE)


def format_posts_list(posts: list[dict[str, Any]], verbose: bool = False) -> None:
    """게시글 목록을 포맷팅합니다.

    Args:
        posts: 게시글 목록
        verbose: 상세 모드
    """
    _print_header(f"Posts List ({len(posts)} items)")

    if not posts:
        print("No posts found.")
        print(SEPARATOR_LINE)
        return

    if verbose:
        for idx, post in enumerate(posts, 1):
            print(f"\n{DASH_LINE}")
            print(f"Post #{idx}")
            print(DASH_LINE)
            format_post(post, verbose=False)
    else:
        header = (
            f"\n{'#':<4} {'Post ID':<10} {'Group':<20} {'Title':<40} "
            f"{'Author':<20} {'Created':<20}"
        )
        print(header)
        divider = f"{'-'*4} {'-'*10} {'-'*20} {'-'*40} {'-'*20} {'-'*20}"
        print(divider)

        for idx, post in enumerate(posts, 1):
            post_id = str(post.get("id", "N/A"))[:10]
            group_name = str(post.get("groupName", "N/A"))[:20]
            title = str(post.get("title", "N/A"))[:40]
            author = str(post.get("authorName", "N/A"))[:20]
            created = _format_timestamp(post.get("createdAt"))[:20]

            row = (
                f"{idx:<4} {post_id:<10} {group_name:<20} {title:<40} "
                f"{author:<20} {created:<20}"
            )
            print(row)

    print(SEPARATOR_LINE)


def format_comment(comment: dict[str, Any]) -> None:
    """댓글 정보를 포맷팅합니다.

    Args:
        comment: 댓글 데이터
    """
    indent = "  " if comment.get("parentId") else ""
    author = comment.get("authorName", "N/A")
    created = _format_timestamp(comment.get("createdAt"))
    text = comment.get("content", {}).get("text", "N/A")[:100]

    print(f"{indent}[{created}] {author}: {text}")


def format_comments_list(comments: list[dict[str, Any]]) -> None:
    """댓글 목록을 포맷팅합니다.

    Args:
        comments: 댓글 목록
    """
    _print_header(f"Comments ({len(comments)} items)")

    if not comments:
        print("No comments found.")
        print(SEPARATOR_LINE)
        return

    for comment in comments:
        format_comment(comment)

    print(SEPARATOR_LINE)


def format_user(user: dict[str, Any], verbose: bool = False) -> None:
    """사용자 정보를 포맷팅합니다.

    Args:
        user: 사용자 데이터
        verbose: 상세 모드
    """
    _print_header(f"User: {user.get('name', 'N/A')}")

    print(f"ID:           {user.get('id', 'N/A')}")
    print(f"Name:         {user.get('name', 'N/A')}")
    print(f"Email:        {user.get('email', 'N/A')}")
    print(f"LDAP ID:      {user.get('ldapId', 'N/A')}")
    print(f"Department:   {user.get('department', 'N/A')}")
    print(f"Position:     {user.get('position', 'N/A')}")

    if verbose:
        print(f"\n{DASH_LINE}")
        print("Full Data:")
        print(DASH_LINE)
        print(json.dumps(user, indent=2, ensure_ascii=False))

    print(SEPARATOR_LINE)


def format_users_list(users: list[dict[str, Any]]) -> None:
    """사용자 목록을 포맷팅합니다.

    Args:
        users: 사용자 목록
    """
    _print_header(f"Users List ({len(users)} items)")

    if not users:
        print("No users found.")
        print(SEPARATOR_LINE)
        return

    print(f"\n{'#':<4} {'User ID':<10} {'Name':<20} {'Email':<30} {'Department':<20}")
    print(f"{'-'*4} {'-'*10} {'-'*20} {'-'*30} {'-'*20}")

    for idx, user in enumerate(users, 1):
        user_id = str(user.get("id", "N/A"))[:10]
        name = str(user.get("name", "N/A"))[:20]
        email = str(user.get("email", "N/A"))[:30]
        dept = str(user.get("department", "N/A"))[:20]

        print(f"{idx:<4} {user_id:<10} {name:<20} {email:<30} {dept:<20}")

    print(SEPARATOR_LINE)


def format_group(group: dict[str, Any], verbose: bool = False) -> None:
    """그룹 정보를 포맷팅합니다.

    Args:
        group: 그룹 데이터
        verbose: 상세 모드
    """
    _print_header(f"Group: {group.get('name', 'N/A')}")

    print(f"ID:           {group.get('id', 'N/A')}")
    print(f"Name:         {group.get('name', 'N/A')}")
    print(f"Description:  {group.get('description', 'N/A')}")
    print(f"Type:         {group.get('type', 'N/A')}")
    print(f"Members:      {group.get('memberCount', 'N/A')}")
    print(f"Created:      {_format_timestamp(group.get('createdAt'))}")

    if verbose:
        print(f"\n{DASH_LINE}")
        print("Full Data:")
        print(DASH_LINE)
        print(json.dumps(group, indent=2, ensure_ascii=False))

    print(SEPARATOR_LINE)


def format_groups_list(groups: list[dict[str, Any]]) -> None:
    """그룹 목록을 포맷팅합니다.

    Args:
        groups: 그룹 목록
    """
    _print_header(f"Groups List ({len(groups)} items)")

    if not groups:
        print("No groups found.")
        print(SEPARATOR_LINE)
        return

    print(f"\n{'#':<4} {'Group ID':<10} {'Name':<30} {'Type':<15} {'Members':<10}")
    print(f"{'-'*4} {'-'*10} {'-'*30} {'-'*15} {'-'*10}")

    for idx, group in enumerate(groups, 1):
        group_id = str(group.get("id", "N/A"))[:10]
        name = str(group.get("name", "N/A"))[:30]
        group_type = str(group.get("type", "N/A"))[:15]
        members = str(group.get("memberCount", "N/A"))[:10]

        print(f"{idx:<4} {group_id:<10} {name:<30} {group_type:<15} {members:<10}")

    print(SEPARATOR_LINE)


def format_party(party: dict[str, Any], verbose: bool = False) -> None:
    """파티(팀) 정보를 포맷팅합니다.

    Args:
        party: 파티 데이터
        verbose: 상세 모드
    """
    _print_header(f"Party: {party.get('name', 'N/A')}")

    print(f"ID:           {party.get('id', 'N/A')}")
    print(f"Name:         {party.get('name', 'N/A')}")
    print(f"Mention ID:   {party.get('mentionId', 'N/A')}")
    print(f"Type:         {party.get('type', 'N/A')}")
    print(f"Members:      {party.get('userCount', 'N/A')}")

    if verbose:
        print(f"\n{DASH_LINE}")
        print("Full Data:")
        print(DASH_LINE)
        print(json.dumps(party, indent=2, ensure_ascii=False))

    print(SEPARATOR_LINE)


def format_templates_list(templates: list[dict[str, Any]]) -> None:
    """템플릿 목록을 포맷팅합니다.

    Args:
        templates: 템플릿 목록
    """
    _print_header(f"Templates List ({len(templates)} items)")

    if not templates:
        print("No templates found.")
        print(SEPARATOR_LINE)
        return

    print(f"\n{'#':<4} {'Template ID':<15} {'Name':<40} {'Use Task':<10}")
    print(f"{'-'*4} {'-'*15} {'-'*40} {'-'*10}")

    for idx, template in enumerate(templates, 1):
        template_id = str(template.get("id", "N/A"))[:15]
        name = str(template.get("name", "N/A"))[:40]
        use_task = str(template.get("useTask", False))[:10]

        print(f"{idx:<4} {template_id:<15} {name:<40} {use_task:<10}")

    print(SEPARATOR_LINE)


if __name__ == "__main__":
    print("This module provides formatting utilities for Agit API results.")
    print("\nAvailable functions:")
    print("  - format_post(post, verbose)")
    print("  - format_posts_list(posts, verbose)")
    print("  - format_comment(comment)")
    print("  - format_comments_list(comments)")
    print("  - format_user(user, verbose)")
    print("  - format_users_list(users)")
    print("  - format_group(group, verbose)")
    print("  - format_groups_list(groups)")
    print("  - format_party(party, verbose)")
    print("  - format_templates_list(templates)")
