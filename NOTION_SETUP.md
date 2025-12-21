# Notion MCP 설정 가이드

ai-env에 Notion MCP 서버를 추가하여 AI 도구에서 Notion 데이터베이스와 페이지에 접근할 수 있습니다.

## Notion API 토큰 발급

### 1. Notion Integration 생성

1. https://www.notion.so/my-integrations 접속
2. "+ New integration" 클릭
3. Integration 정보 입력:
   - **Name**: 예) "AI Environment MCP"
   - **Associated workspace**: 사용할 워크스페이스 선택
   - **Type**: Internal integration
4. "Submit" 클릭
5. **Internal Integration Token** 복사 (형식: `ntn_...`)

### 2. Integration에 페이지 접근 권한 부여

Notion Integration은 기본적으로 아무 페이지에도 접근할 수 없습니다. 각 페이지/데이터베이스에 명시적으로 권한을 부여해야 합니다:

1. Notion에서 공유하고 싶은 페이지 열기
2. 우측 상단 "Share" 또는 "..." 메뉴 클릭
3. "Invite" 입력란에 Integration 이름 입력
4. Integration 선택하여 초대

**또는 데이터베이스의 경우:**
1. 데이터베이스 페이지 열기
2. 우측 상단 "..." 메뉴 → "Connections" 클릭
3. Integration 선택

## 환경변수 설정

`.env` 파일에 Notion API 토큰 추가:

```bash
# .env 파일 편집
vi .env

# 다음 줄 추가:
# NOTION_API_TOKEN=ntn_your_token_here
```

확인 및 동기화:

```bash
# 등록 확인
uv run ai-env secrets

# 설정 동기화
uv run ai-env sync
```

## 사용 가능한 기능

Notion MCP 서버를 통해 다음 작업을 수행할 수 있습니다:

### 페이지 검색 및 조회
```
User: "Notion에서 'Meeting Notes' 제목의 페이지 찾아줘"
Claude: [검색 결과 표시]

User: "해당 페이지 내용 보여줘"
Claude: [페이지 내용 조회]
```

### 데이터베이스 작업
```
User: "Tasks 데이터베이스의 완료되지 않은 항목 보여줘"
Claude: [데이터베이스 필터링 및 조회]

User: "새로운 Task 추가해줘: '문서 작성'"
Claude: [데이터베이스에 항목 생성]
```

### 페이지 생성 및 수정
```
User: "새 페이지 만들고 제목은 'Weekly Report'로 해줘"
Claude: [페이지 생성]

User: "이 페이지에 오늘 한 일 3가지 추가해줘"
Claude: [페이지 내용 업데이트]
```

## 사용 예시

### 회의록 정리
```
User: "오늘 회의록을 Notion에 정리해줘. 제목은 '2025-01-15 팀 회의'로"
Claude: [페이지 생성 후 내용 작성]
```

### 작업 관리
```
User: "Notion Tasks 데이터베이스에서 내가 할당된 항목 중 우선순위가 높은 것들 보여줘"
Claude: [데이터베이스 쿼리 실행]

User: "완료된 항목들을 'Done' 상태로 변경해줘"
Claude: [데이터베이스 항목 업데이트]
```

### 지식 베이스 검색
```
User: "Notion에서 'Python 코딩 가이드' 관련 페이지 찾아서 내용 요약해줘"
Claude: [검색 후 페이지 내용 요약]
```

## 주의사항

### 권한 관리

⚠️ **Integration에 명시적으로 공유된 페이지만 접근 가능합니다**
- 새로운 페이지/데이터베이스를 사용하려면 Integration을 다시 초대해야 함
- 워크스페이스 전체 접근 권한은 없음 (보안을 위해)

### API 제한

Notion API에는 Rate Limit이 있습니다:
- 초당 평균 3 requests
- 대량 작업 시 자동으로 속도 조절됨

### 토큰 보안

- `.env` 파일은 절대 Git에 커밋하지 마세요
- Integration Token이 노출되면 즉시 재생성하세요
- 필요한 최소한의 페이지만 공유하세요

## 트러블슈팅

### "Could not find page" 에러

**원인**: Integration이 해당 페이지에 접근 권한이 없음

**해결**:
1. Notion에서 페이지 열기
2. Share 메뉴에서 Integration 초대
3. 다시 시도

### "Unauthorized" 에러

**원인**: API 토큰이 잘못되었거나 만료됨

**해결**:
```bash
# .env 파일에서 토큰 업데이트
vi .env
# NOTION_API_TOKEN을 새 값으로 변경

# 재동기화
uv run ai-env sync
```

### MCP 서버 연결 실패

**확인사항**:
1. 토큰 등록 확인:
   ```bash
   uv run ai-env secrets
   ```

2. 설정 동기화 확인:
   ```bash
   uv run ai-env sync
   ```

3. AI 도구 재시작 (Claude Desktop, Antigravity 등)

## 참고 자료

- [Notion API 공식 문서](https://developers.notion.com/)
- [Notion MCP Server GitHub](https://github.com/modelcontextprotocol/servers/tree/main/src/notion)
- [Integration 권한 관리](https://www.notion.so/help/add-and-manage-connections-with-the-api)

## FAQ

**Q: 모든 페이지를 한 번에 공유할 수 없나요?**
A: 보안상의 이유로 각 페이지마다 개별적으로 Integration을 초대해야 합니다. 하지만 상위 페이지에 초대하면 하위 페이지들도 자동으로 접근 가능합니다.

**Q: 여러 워크스페이스를 사용하는데 어떻게 하나요?**
A: 각 워크스페이스마다 별도의 Integration과 토큰이 필요합니다. `config/mcp_servers.yaml`에서 여러 Notion 서버를 설정할 수 있습니다.

**Q: 데이터베이스 스키마를 변경할 수 있나요?**
A: 네, API를 통해 속성(properties) 추가/수정이 가능합니다. 하지만 삭제는 제한적입니다.
