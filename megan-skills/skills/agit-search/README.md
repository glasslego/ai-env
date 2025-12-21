# Agit Search Skill

Agit Bot API v2를 사용하여 그룹, 게시글(wall_messages), 댓글을 조회하는 skill입니다.

## 빠른 시작

### 1. 환경 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집
# AGIT_BOT_TOKEN=your_actual_token_here
```

### 2. 의존성 설치 (선택)

```bash
pip install python-dotenv
```

> python-dotenv가 없어도 환경변수가 설정되어 있으면 동작합니다.

### 3. 사용 예제

```python
import sys

sys.path.append('.claude/skills/agit-search/scripts')
from agit_client import AgitClient, load_agit_token

# Load token from .env (또는 환경변수)
token = load_agit_token()

# Initialize client
client = AgitClient(token=token)

# Get groups
groups = client.get_groups(limit=10)
print(f"Found {len(groups)} groups")

# Get wall message
message = client.get_wall_message(wall_message_id=444958917)
print(f"Message: {message['text'][:100]}")

# Get wall messages from group
messages = client.get_wall_messages(group_id=300068539, limit=5)
for msg in messages:
    print(f"{msg['id']}: {msg.get('text', '')[:50]}")

# Search user's posts
posts = client.search_wall_messages_by_user(
    user_email="user@kakao.com",
    max_groups=20
)
print(f"Found {len(posts)} posts")
```

## Bot Token 발급

1. https://kakao.agit.in/build/apps 에서 앱 생성
2. Bot 사용자 추가
3. 필요한 스코프 정의
4. 워크스페이스에 앱 설치
5. Access Token 획득 (완전한 JWT 형식: header.payload.signature)
6. .env 파일에 토큰 저장

## 상세 문서

- [SKILL.md](SKILL.md) - 상세 사용 가이드
- [references/api_endpoints.md](references/api_endpoints.md) - API 엔드포인트
- [references/data_structures.md](references/data_structures.md) - 데이터 구조

## 주요 기능

- ✅ 그룹 목록 조회
- ✅ 게시글(wall_messages) 조회 및 검색
- ✅ 댓글 조회
- ✅ 사용자별 게시글 검색 (email, name, LDAP ID)
- ✅ 대화(conversations) 조회
- ✅ .env 파일 지원 (python-dotenv)

## API 엔드포인트

- `GET /v2/groups` - 그룹 목록
- `GET /v2/wall_messages?group_id={id}` - 그룹의 게시글 목록
- `GET /v2/wall_messages/{id}` - 특정 게시글 조회
- `GET /v2/wall_messages/{id}/comments` - 댓글 목록
- `GET /v2/conversations.list` - 대화 목록

## 트러블슈팅

### Token 문제
- Token이 완전한 JWT 형식인지 확인 (3개 파트, 점으로 구분)
- 예: `eyJxxx.eyJyyy.zzz`

### 403 / 404 에러
- Bot이 해당 그룹에 추가되었는지 확인
- Bot Token 권한 확인

### Connection Error
- VPN 연결 확인
- API URL: https://api.agit.in
