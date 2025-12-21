# ai-env 프로젝트 Command

## 사용법
Claude Code에서 `/project:setup` 형태로 실행

---

# Setup: 새 프로젝트에 ai-env 환경 적용
---
description: 현재 프로젝트에 ai-env 표준 환경설정을 적용합니다
---

다음 단계를 순서대로 실행해주세요:

1. **현재 프로젝트 분석**
   - 프로젝트 타입 확인 (Python/Node/etc)
   - 기존 .env 파일 존재 여부 확인
   - 기존 MCP 설정 확인

2. **ai-env 연동**
   - /Users/megan/work/ai-env/.env 를 참조할 수 있도록 심볼릭 링크 또는 source 설정
   - 또는 필요한 환경변수만 복사

3. **MCP 설정 적용**
   - .claude/settings.local.json 생성
   - .codex/config.toml 생성
   - .gemini/settings.local.json 생성

4. **프로젝트별 CLAUDE.md 생성**
   - /init 명령 실행하여 코드베이스 분석
   - ai-env 표준 규칙 추가

5. **결과 보고**
   - 적용된 설정 요약
   - 추가 설정 권장사항
