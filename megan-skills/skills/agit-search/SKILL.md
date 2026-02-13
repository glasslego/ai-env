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

Agit Bot API v2를 통해 그룹, 게시글(wall_messages), 댓글을 조회합니다.

## 초기 설정

```bash
# .env 파일에 토큰 설정
# AGIT_BOT_TOKEN=your_actual_bot_token_here

# Bot Token 발급: https://kakao.agit.in/build/apps → 앱 생성 → Bot 추가 → 스코프 정의 → 설치
```

## 사용 방법

```python
import sys
sys.path.append('.claude/skills/agit-search/scripts')
from agit_client import AgitClient, load_agit_token

client = AgitClient(token=load_agit_token())
```

### 그룹 조회

```python
groups = client.get_groups(limit=50)
```

### 게시글 (Wall Messages)

```python
# 그룹의 게시글 목록
messages = client.get_wall_messages(group_id=300068539, limit=20, latest=None, oldest=None)

# 특정 게시글 상세
message = client.get_wall_message(wall_message_id=444958917)
# message['text'], message['user'], message['content_data']['task'], message['reactions']
```

### 댓글

```python
comments = client.get_wall_message_comments(wall_message_id=444958917, limit=50)
```

### 대화

```python
conversations = client.get_conversations()
```

### 사용자 검색

```python
# 이메일/이름/LDAP ID로 검색 (결과는 created_time 기준 내림차순)
posts = client.search_wall_messages_by_user(user_email="user@kakao.com", max_groups=50)
posts = client.search_wall_messages_by_user(user_name="홍길동", max_groups=50)
posts = client.search_wall_messages_by_user(ldap_id="username", max_groups=50)
```

## 트러블슈팅

| 에러 | 원인 |
|------|------|
| 403 not_in_conversation | Bot이 그룹에 추가되지 않음 |
| 404 group_not_found | group_id 오류 또는 접근 권한 없음 |
| 401 Unauthorized | Token 만료/오류. JWT 형식(3파트) 확인 |
| Connection Error | VPN 확인, base URL: https://api.agit.in |

## 참고 문서

- `references/api_endpoints.md` - API 엔드포인트 목록
- `references/data_structures.md` - 데이터 구조 (Wall Message, Comment 등)
- `scripts/agit_client.py` - API 클라이언트 구현
