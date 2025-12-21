# Agit Bot API v2 Endpoints

Agit Bot API v2 엔드포인트 목록입니다.

## Base URL

- Production: `https://api.agit.in`
- Base path: `/v2`

## Authentication

모든 요청은 Bearer Token 인증 필요:

```http
Authorization: Bearer {AGIT_BOT_TOKEN}
```

## Groups (그룹)

### List Groups
```
GET /v2/groups
```

접근 가능한 그룹 목록을 조회합니다.

**Parameters:**
- `limit` (optional): 조회할 그룹 수

**Response:**
```json
{
  "groups": [
    {
      "id": 300068539,
      "name": "그룹명",
      ...
    }
  ]
}
```

## Wall Messages (게시글)

### List Wall Messages
```
GET /v2/wall_messages?group_id={group_id}&limit={limit}
```

그룹의 게시글 목록을 조회합니다.

**Parameters:**
- `group_id` (required): 그룹 ID
- `limit` (optional): 조회할 게시글 수 (default: 20)
- `latest` (optional): 이 ID 이전의 게시글 (pagination)
- `oldest` (optional): 이 ID 이후의 게시글 (pagination)

**Response:**
```json
{
  "wall_messages": [
    {
      "id": 444958917,
      "text": "게시글 내용...",
      "group_id": 300068539,
      "actor_id": 743649,
      "created_time": 1763012958,
      "updated_time": 1763418218,
      "is_parent": true,
      "first_thread_id": 444958917,
      "user": {
        "id": 300051824,
        "name": "사용자명",
        "email": "user@kakao.com",
        "ldap_id": "username",
        "profile_image_url": "https://..."
      },
      "content_data": {
        "task": [...],
        "image": [...]
      },
      "reactions": [
        {
          "reaction_type": 3,
          "count": 2,
          "actors": [300044433, 300051824]
        }
      ]
    }
  ]
}
```

### Get Wall Message
```
GET /v2/wall_messages/{wall_message_id}
```

특정 게시글을 조회합니다.

**Response:**
```json
{
  "wall_message": {
    "id": 444958917,
    "text": "게시글 내용...",
    "group_id": 300068539,
    "actor_id": 743649,
    "created_time": 1763012958,
    "updated_time": 1763418218,
    "is_parent": true,
    "first_thread_id": 444958917,
    "is_comments_closed": false,
    "feed_template_id": 0,
    "group_message_template_id": 38894,
    "task_status": null,
    "content_data": { ... },
    "reactions": [ ... ]
  }
}
```

### Get Wall Message Comments
```
GET /v2/wall_messages/{wall_message_id}/comments
```

게시글의 댓글 목록을 조회합니다.

**Parameters:**
- `limit` (optional): 조회할 댓글 수

**Response:**
```json
{
  "comments": [
    {
      "id": 12345,
      "text": "댓글 내용...",
      "wall_message_id": 444958917,
      "user": {
        "id": 300051824,
        "name": "사용자명",
        "email": "user@kakao.com"
      },
      "created_time": 1763012958
    }
  ]
}
```

## Conversations (대화)

### List Conversations
```
GET /v2/conversations.list
```

접근 가능한 대화 목록을 조회합니다.

**Response:**
```json
{
  "conversations": [
    {
      "id": "conv-123",
      "name": "대화방 이름",
      "type": "channel",
      ...
    }
  ],
  "meta": {
    "next_cursor": "cGFnZT0y"
  }
}
```

### Get Conversation Info
```
GET /v2/conversations.info
```

대화 상세 정보를 조회합니다.

**Parameters:**
- `conversation` (optional): 대화 ID

**Response:**
```json
{
  "conversations": [],
  "meta": {
    "next_cursor": "cGFnZT0y"
  }
}
```

### Get Conversation Messages
```
GET /v2/conversations.messages
```

대화의 메시지 목록을 조회합니다.

**Parameters:**
- `conversation` (required): 대화 ID
- `limit` (optional): 조회할 메시지 수

**Response:**
```json
{
  "messages": [
    {
      "id": "msg-123",
      "text": "메시지 내용...",
      "user": { ... },
      "created_at": "2025-11-13T14:49:18.000+09:00"
    }
  ]
}
```

## Webhook (메시지 전송)

### Send Message
```
POST https://agit.in/webhook/{webhook_token}
Content-Type: application/json

{
  "text": "전송할 메시지 내용"
}
```

Webhook을 통해 메시지를 전송합니다.

**Note**: 이 엔드포인트는 Bot API가 아닌 별도 webhook 엔드포인트입니다.

## Error Codes

### 400 Bad Request
- `invalid_users`: 잘못된 사용자 정보
- `group_not_found`: 그룹을 찾을 수 없음

### 401 Unauthorized
- `invalid_authorization_header`: Bot token이 없거나 유효하지 않음
- Token이 만료됨

### 403 Forbidden
- `not_in_conversation`: Bot이 해당 대화에 참여하지 않음
- Bot이 해당 리소스에 접근 권한이 없음

### 404 Not Found
- 요청한 리소스가 존재하지 않음
- ID가 잘못됨

### 500 Internal Server Error
- 서버 오류
- Agit 팀에 문의

## Rate Limiting

- API 사용량 제한이 있을 수 있음
- 429 Too Many Requests 발생 시 잠시 후 재시도

## Timestamps

- `created_time`, `updated_time`: Unix timestamp (seconds)
- `created_at`, `updated_at`: ISO 8601 format string
- Python: `datetime.fromtimestamp(created_time)`
- JavaScript: `new Date(created_time * 1000)`

## Pagination

- `limit`: 한 번에 조회할 항목 수
- `latest`: 이 ID 이전의 항목 조회 (더 오래된 항목)
- `oldest`: 이 ID 이후의 항목 조회 (더 최신 항목)
- `next_cursor`: 다음 페이지 커서 (일부 엔드포인트)

## Field Naming Convention

- Snake case: `wall_message_id`, `created_time`, `user_id`
- Camel case도 일부 사용: `createdAt`, `groupId` (응답에 따라 다름)
- ID 필드는 정수형 또는 문자열
