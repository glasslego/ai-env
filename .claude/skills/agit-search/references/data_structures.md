# Agit Bot API v2 Data Structures

Agit Bot API v2 응답 데이터 구조입니다.

## Wall Message (게시글)

```python
{
    "id": 444958917,                          # 게시글 ID
    "text": "*[업무 요청]*\n...",             # 게시글 내용 (마크다운)
    "group_id": 300068539,                    # 그룹 ID
    "actor_id": 743649,                       # 작성자 ID (actor)
    "created_time": 1763012958,               # Unix timestamp (seconds)
    "updated_time": 1763418218,               # Unix timestamp (seconds)
    "modified_time": null,                    # 수정 시간
    "is_parent": true,                        # 상위 스레드 여부
    "first_thread_id": 444958917,             # 첫 번째 스레드 ID
    "is_comments_closed": false,              # 댓글 닫힘 여부
    "feed_template_id": 0,                    # 피드 템플릿 ID
    "group_message_template_id": 38894,       # 그룹 메시지 템플릿 ID
    "task_status": null,                      # 작업 상태
    "user": {                                 # 작성자 정보 (선택)
        "id": 300051824,
        "name": "사용자명",
        "email": "user@kakao.com",
        "ldap_id": "username",
        "profile_image_url": "https://mk.kakaocdn.net/..."
    },
    "content_data": {                         # 콘텐츠 데이터
        "task": [                             # 작업 정보
            {
                "id": 14307449,
                "group_id": 300068539,
                "user_id": 743649,
                "wall_message_id": 444958917,
                "status": 0,                  # 0: 진행중, 1: 완료 등
                "created_at": "2025-11-13T14:49:18.000+09:00",
                "updated_at": "2025-11-13T14:49:18.000+09:00",
                "assignees": [                # 담당자 목록
                    {
                        "id": 300039954,
                        "agit_id": "tim.kim",
                        "profile_image_url": "https://..."
                    }
                ]
            }
        ],
        "image": [                            # 이미지 첨부
            {
                "id": "image-123",
                "url": "https://...",
                "width": 1920,
                "height": 1080
            }
        ]
    },
    "reactions": [                            # 반응 목록
        {
            "reaction_type": 3,               # 1: 좋아요, 2: 하트, 3: 체크, 4: 박수
            "count": 2,
            "actors": [300044433, 300051824]  # 반응한 사용자 ID 목록
        }
    ]
}
```

## Comment (댓글)

```python
{
    "id": 12345,                              # 댓글 ID
    "text": "댓글 내용...",                    # 댓글 텍스트
    "wall_message_id": 444958917,             # 게시글 ID
    "parent_id": null,                        # 부모 댓글 ID (대댓글인 경우)
    "created_time": 1763012958,               # Unix timestamp (seconds)
    "updated_time": 1763418218,
    "user": {                                 # 작성자 정보
        "id": 300051824,
        "name": "사용자명",
        "email": "user@kakao.com",
        "ldap_id": "username",
        "profile_image_url": "https://..."
    },
    "reactions": [                            # 반응 목록 (댓글에도 적용)
        {
            "reaction_type": 1,
            "count": 5,
            "actors": [...]
        }
    ]
}
```

## User (사용자)

```python
{
    "id": 300051824,                          # 사용자 ID
    "name": "홍길동",                         # 이름
    "email": "user@kakao.com",                # 이메일
    "ldap_id": "username",                    # LDAP ID
    "agit_id": "username",                    # Agit ID (ldap_id와 동일할 수 있음)
    "profile_image_url": "https://mk.kakaocdn.net/...",  # 프로필 이미지
    "department": "개발본부",                 # 부서 (선택)
    "position": "책임매니저",                 # 직책 (선택)
    "status": "active"                        # 상태 (선택)
}
```

## Group (그룹)

```python
{
    "id": 300068539,                          # 그룹 ID
    "name": "그룹명",                         # 그룹 이름
    "description": "그룹 설명",               # 설명 (선택)
    "type": "PUBLIC",                         # PUBLIC, PRIVATE, SECRET
    "member_count": 25,                       # 멤버 수 (선택)
    "created_at": "2025-11-13T14:49:18.000+09:00",
    "owner": {                                # 소유자 정보 (선택)
        "id": 300051824,
        "name": "홍길동"
    }
}
```

## Conversation (대화)

```python
{
    "id": "conv-123",                         # 대화 ID
    "name": "대화방 이름",                    # 대화방 이름
    "type": "channel",                        # channel, direct, group
    "members": [                              # 참여자 목록 (선택)
        {
            "id": 300051824,
            "name": "홍길동"
        }
    ],
    "created_at": "2025-11-13T14:49:18.000+09:00"
}
```

## Task (작업)

```python
{
    "id": 14307449,                           # 작업 ID
    "group_id": 300068539,                    # 그룹 ID
    "user_id": 743649,                        # 작성자 ID
    "wall_message_id": 444958917,             # 게시글 ID
    "status": 0,                              # 상태: 0=진행중, 1=완료
    "created_at": "2025-11-13T14:49:18.000+09:00",
    "updated_at": "2025-11-13T14:49:18.000+09:00",
    "assignees": [                            # 담당자 목록
        {
            "id": 300039954,
            "agit_id": "tim.kim",
            "profile_image_url": "https://..."
        }
    ]
}
```

## Reaction (반응)

```python
{
    "reaction_type": 3,                       # 반응 타입
    "count": 2,                               # 반응 수
    "actors": [300044433, 300051824]          # 반응한 사용자 ID 목록
}
```

### Reaction Types

| Type | 의미 |
|------|------|
| 1 | 좋아요 👍 |
| 2 | 하트 ❤️ |
| 3 | 체크 ✅ |
| 4 | 박수 👏 |

## Pagination Response

목록 API는 다음 형식으로 응답합니다:

```python
{
    "wall_messages": [...],               # 또는 groups, comments, conversations 등
    "meta": {                             # 메타 정보 (선택)
        "next_cursor": "cGFnZT0y",        # 다음 페이지 커서
        "has_more": true                  # 더 많은 데이터 존재 여부
    }
}
```

## Content Data Types

### Task Content
```python
{
    "task": [
        {
            "id": 14307449,
            "status": 0,
            "assignees": [...]
        }
    ]
}
```

### Image Content
```python
{
    "image": [
        {
            "id": "image-123",
            "url": "https://...",
            "width": 1920,
            "height": 1080,
            "thumbnail_url": "https://..."      # 썸네일 (선택)
        }
    ]
}
```

### File Content
```python
{
    "file": [
        {
            "id": "file-123",
            "name": "document.pdf",
            "size": 1024000,                    # bytes
            "url": "https://...",
            "mime_type": "application/pdf"
        }
    ]
}
```

## Mentions (멘션)

텍스트 내 멘션 정보는 마크다운 링크 형식으로 표시됩니다:

```
[@username](https://kakao.agit.in/users/300051824)      # 사용자 멘션
[@@team](https://kakao.agit.in/parties/13560)           # 팀/파티 멘션
```

## Timestamps

### Unix Timestamp (seconds)
- `created_time`, `updated_time`, `modified_time`
- Python: `datetime.fromtimestamp(created_time)`
- JavaScript: `new Date(created_time * 1000)`

### ISO 8601 String
- `created_at`, `updated_at`
- Format: `"2025-11-13T14:49:18.000+09:00"`
- Python: `datetime.fromisoformat(created_at)`
- JavaScript: `new Date(created_at)`

## Field Naming Convention

### Snake Case (주로 사용)
- `wall_message_id`
- `created_time`
- `user_id`
- `group_id`
- `is_parent`

### Camel Case (일부 사용)
- `createdAt`
- `updatedAt`
- `groupId` (응답에 따라 다를 수 있음)

### ID 필드
- 정수형: `300051824` (사용자, 그룹, 게시글 ID)
- 문자열: `"conv-123"` (일부 대화 ID)

## Boolean 값

- `is_parent`: 상위 스레드 여부
- `is_comments_closed`: 댓글 닫힘 여부
- `has_more`: 더 많은 데이터 존재 여부

## Null 값

null 값은 해당 필드가 설정되지 않았거나 없음을 의미:
- `modified_time`: null (수정되지 않음)
- `task_status`: null (작업 상태 없음)
- `parent_id`: null (최상위 댓글)
