---
name: agit-search
description: Agit Bot API v2를 사용하여 그룹, 게시글(wall_messages), 댓글을 조회합니다.
  - Agit는 카카오의 사내 협업 도구입니다
  - Bot API v2를 통해 그룹, 게시글, 댓글, 대화 정보를 조회할 수 있습니다
  - Bearer Token 인증 필요 (AGIT_BOT_TOKEN 환경변수)

  Use this skill when user needs to:
  - Search or view Agit wall messages (posts) and comments
  - Get group information
  - Search user's posts by email or name
  - Get conversation information
  - Analyze Agit collaboration data
---

# Agit Search Skill

이 스킬은 Agit Bot API v2를 통해 그룹, 게시글(wall_messages), 댓글을 조회합니다.

## 사용 방법

### 0. 환경 설정 (최초 1회)

**1. .env 파일 생성**

```bash
# .env.example을 복사하여 .env 파일 생성
cp .claude/skills/agit-search/.env.example .claude/skills/agit-search/.env

# .env 파일 편집하여 실제 토큰 입력
# AGIT_BOT_TOKEN=your_actual_bot_token_here
```

**2. python-dotenv 설치 (선택)**

```bash
pip install python-dotenv
```

> **Note**: python-dotenv가 없어도 환경변수가 설정되어 있으면 동작합니다.

### 1. 설정 로드

```python
import sys

sys.path.append('.claude/skills/agit-search/scripts')
from agit_client import AgitClient, load_agit_token

# Load token from .env file (or environment variable)
bot_token = load_agit_token()

# Initialize client
client = AgitClient(token=bot_token)
```

### 2. API 클라이언트 사용

```python
# Get groups
groups = client.get_groups(limit=50)

# Get wall messages from a group
messages = client.get_wall_messages(group_id=300068539, limit=20)

# Get specific wall message
message = client.get_wall_message(wall_message_id=444958917)

# Get comments
comments = client.get_wall_message_comments(wall_message_id=444958917)

# Search user's posts
posts = client.search_wall_messages_by_user(
    user_email="user@kakao.com",
    max_groups=50,
    messages_per_group=20
)
```

## 주요 기능

### 그룹 (Groups)

#### 그룹 목록 조회
```python
groups = client.get_groups(limit=100)
for group in groups:
    print(f"Group ID: {group['id']}")
```

### 게시글 (Wall Messages)

#### 그룹의 게시글 목록 조회
```python
messages = client.get_wall_messages(
    group_id=300068539,
    limit=20,          # 조회할 개수 (default: 20)
    latest=None,       # 이 ID 이전 게시글
    oldest=None        # 이 ID 이후 게시글
)
for msg in messages:
    print(f"{msg['id']}: {msg.get('text', '')[:50]}")
```

#### 특정 게시글 조회
```python
message = client.get_wall_message(wall_message_id=444958917)
print(f"Text: {message['text']}")
print(f"Group: {message['group_id']}")
print(f"Created: {message['created_time']}")

# 작성자 정보
user = message.get('user', {})
print(f"Author: {user.get('name')} ({user.get('email')})")

# 작업 정보
content_data = message.get('content_data', {})
if content_data.get('task'):
    for task in content_data['task']:
        print(f"Task ID: {task['id']}, Status: {task['status']}")
        for assignee in task.get('assignees', []):
            print(f"  Assignee: {assignee['agit_id']}")

# 반응
for reaction in message.get('reactions', []):
    reaction_types = {1: '좋아요', 2: '하트', 3: '체크', 4: '박수'}
    r_type = reaction_types.get(reaction['reaction_type'], 'Unknown')
    print(f"{r_type}: {reaction['count']}개")
```

### 댓글 (Comments)

#### 게시글 댓글 조회
```python
comments = client.get_wall_message_comments(
    wall_message_id=444958917,
    limit=50
)
for comment in comments:
    user = comment.get('user', {})
    print(f"{user.get('name')}: {comment.get('text')}")
```

### 대화 (Conversations)

#### 대화 목록 조회
```python
conversations = client.get_conversations()
for conv in conversations:
    print(f"{conv['id']}: {conv.get('name', 'N/A')}")
```

### 사용자 검색

#### 사용자의 게시글 검색
```python
# 이메일로 검색
posts = client.search_wall_messages_by_user(
    user_email="user@kakao.com",
    max_groups=50,              # 검색할 최대 그룹 수
    messages_per_group=20       # 그룹당 조회할 메시지 수
)

# 이름으로 검색
posts = client.search_wall_messages_by_user(
    user_name="홍길동",
    max_groups=50
)

# LDAP ID로 검색
posts = client.search_wall_messages_by_user(
    ldap_id="username",
    max_groups=50
)

# 결과 출력 (created_time 기준 내림차순 정렬됨)
for post in posts:
    user = post.get('user', {})
    print(f"ID: {post['id']}")
    print(f"Author: {user.get('name')} ({user.get('email')})")
    print(f"Text: {post.get('text', '')[:100]}")
    print()
```

## 설정

### 환경변수

```bash
# Agit Bot Token (필수)
export AGIT_BOT_TOKEN="your-bot-token-here"
```

### Bot Token 발급 방법

1. https://kakao.agit.in/build/apps 에서 앱 생성
2. Bot 사용자 추가
3. 필요한 스코프 정의
4. 워크스페이스에 앱 설치하여 Access Token 획득
5. .env 파일에 토큰 저장

## API 엔드포인트

주요 엔드포인트:

- `GET /v2/groups` - 그룹 목록
- `GET /v2/wall_messages?group_id={id}` - 그룹의 게시글 목록
- `GET /v2/wall_messages/{id}` - 특정 게시글 조회
- `GET /v2/wall_messages/{id}/comments` - 댓글 목록
- `GET /v2/conversations.list` - 대화 목록

## 데이터 구조

### Wall Message (게시글)
```python
{
    "id": 444958917,
    "text": "게시글 내용...",
    "group_id": 300068539,
    "actor_id": 743649,
    "created_time": 1763012958,        # Unix timestamp (seconds)
    "updated_time": 1763418218,
    "is_parent": true,
    "first_thread_id": 444958917,
    "user": {
        "id": 300051824,
        "name": "사용자명",
        "email": "user@kakao.com",
        "ldap_id": "username"
    },
    "content_data": {
        "task": [...],
        "image": [...]
    },
    "reactions": [
        {
            "reaction_type": 3,        # 1:좋아요, 2:하트, 3:체크, 4:박수
            "count": 2,
            "actors": [...]
        }
    ]
}
```

### Comment (댓글)
```python
{
    "id": 12345,
    "text": "댓글 내용...",
    "wall_message_id": 444958917,
    "user": {...},
    "created_time": 1763012958
}
```

## 참고 문서

- `references/api_endpoints.md` - API 엔드포인트 목록
- `references/data_structures.md` - 데이터 구조 설명
- `scripts/agit_client.py` - API 클라이언트 구현
- `README.md` - 빠른 시작 가이드

## 주의사항

1. **인증 필수**: 모든 API 요청은 Bearer Token 인증 필요
2. **Bot 권한**: Bot이 접근할 수 있는 그룹/대화만 조회 가능
3. **Rate Limiting**: API 사용량 제한 있을 수 있음
4. **VPN**: 사내 네트워크 접근 필요할 수 있음
5. **User 필드**: 일부 응답에서 user 필드가 비어있을 수 있음 (actor_id 사용)

## 트러블슈팅

### 403 Forbidden / not_in_conversation
- Bot이 해당 그룹이나 대화에 추가되지 않음
- Bot을 그룹에 먼저 추가해야 함

### 404 Not Found / group_not_found
- group_id가 잘못되었거나 Bot이 접근 권한이 없음
- Bot Token이 유효한지 확인

### 401 Unauthorized
- Bot Token이 올바른지 확인
- Token이 만료되지 않았는지 확인
- .env 파일의 토큰이 완전한 JWT 형식인지 확인 (3개 파트, 점으로 구분)

### Connection Error
- VPN 연결 확인
- API base URL 확인 (https://api.agit.in)
- 네트워크 연결 확인

## 사용 예제

```python
import sys
sys.path.append('.claude/skills/agit-search/scripts')
from agit_client import AgitClient, load_agit_token

# Initialize
token = load_agit_token()
client = AgitClient(token=token)

# 1. 그룹 목록 조회
groups = client.get_groups(limit=10)
print(f"Found {len(groups)} groups")

# 2. 특정 그룹의 최신 게시글 조회
if groups:
    group_id = groups[0]['id']
    messages = client.get_wall_messages(group_id=group_id, limit=5)
    print(f"Found {len(messages)} messages in group {group_id}")

# 3. 특정 게시글 상세 조회
message = client.get_wall_message(444958917)
print(f"Message: {message['text'][:100]}")

# 4. 댓글 조회
comments = client.get_wall_message_comments(444958917)
print(f"Found {len(comments)} comments")

# 5. 사용자 검색
posts = client.search_wall_messages_by_user(
    user_email="user@kakao.com",
    max_groups=20
)
print(f"Found {len(posts)} posts by user")
```
