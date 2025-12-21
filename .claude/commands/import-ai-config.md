# Import AI Config

ai-env의 글로벌 Claude 설정(commands, skills, settings)을 현재 프로젝트로 가져옵니다.
**기본 동작: 심볼릭 링크로 전체 항목(commands, skills, settings.glocal.json) 가져오기**

## 사용법

```
/import-ai-config [options]
```

## 옵션

- `--source PATH`: 소스 .claude 디렉토리 경로 (기본값: /Users/megan/work/ai-env/.claude)
- `--copy`: 파일 복사 방식 (기본값은 심볼릭 링크)
- `--commands-only`: commands만 가져오기
- `--skills-only`: skills만 가져오기
- `--settings-only`: settings.glocal.json만 가져오기

## 인자

$ARGUMENTS

---

## 작업 시작

### 1. 소스 경로 결정

인자에서 `--source PATH`가 주어지면 해당 경로 사용, 없으면 기본값 사용:
- 기본 소스: `/Users/megan/work/ai-env/.claude`

### 2. 옵션 파싱

- `--copy` 옵션이 있으면 복사 방식, 없으면 심볼릭 링크 방식
- `--commands-only`, `--skills-only`, `--settings-only` 옵션이 없으면 전체 가져오기

### 3. 실행

#### 3-1. .claude 디렉토리 생성 (없으면)

```bash
mkdir -p .claude
```

#### 3-2. 기존 파일 백업 및 심볼릭 링크 생성 (기본값)

```bash
SOURCE="/Users/megan/work/ai-env/.claude"

# 기존 디렉토리/파일 백업 (심볼릭 링크가 아닌 경우만)
[ -e .claude/commands ] && [ ! -L .claude/commands ] && mv .claude/commands .claude/commands.bak.$(date +%Y%m%d%H%M%S)
[ -e .claude/skills ] && [ ! -L .claude/skills ] && mv .claude/skills .claude/skills.bak.$(date +%Y%m%d%H%M%S)
[ -e .claude/settings.glocal.json ] && [ ! -L .claude/settings.glocal.json ] && mv .claude/settings.glocal.json .claude/settings.glocal.json.bak.$(date +%Y%m%d%H%M%S)

# 기존 심볼릭 링크 제거
[ -L .claude/commands ] && rm .claude/commands
[ -L .claude/skills ] && rm .claude/skills
[ -L .claude/settings.glocal.json ] && rm .claude/settings.glocal.json

# 심볼릭 링크 생성
ln -s "$SOURCE/commands" .claude/commands
ln -s "$SOURCE/skills" .claude/skills
ln -s "$SOURCE/settings.glocal.json" .claude/settings.glocal.json
```

#### 3-3. 파일 복사 방식 (--copy 옵션 시)

```bash
SOURCE="/Users/megan/work/ai-env/.claude"

# 기존 디렉토리/파일 백업
[ -e .claude/commands ] && mv .claude/commands .claude/commands.bak.$(date +%Y%m%d%H%M%S)
[ -e .claude/skills ] && mv .claude/skills .claude/skills.bak.$(date +%Y%m%d%H%M%S)
[ -e .claude/settings.glocal.json ] && mv .claude/settings.glocal.json .claude/settings.glocal.json.bak.$(date +%Y%m%d%H%M%S)

# 파일 복사
cp -r "$SOURCE/commands" .claude/
cp -r "$SOURCE/skills" .claude/
cp "$SOURCE/settings.glocal.json" .claude/
```

### 4. settings.local.json 처리

settings.local.json이 없으면 기본 템플릿 생성:

```bash
if [ ! -f .claude/settings.local.json ]; then
  cat > .claude/settings.local.json << 'EOF'
{
  "permissions": {
    "allow": [],
    "deny": []
  }
}
EOF
fi
```

### 5. 결과 확인 및 요약

```bash
ls -la .claude/
```

성공 시 출력:
- ✓ commands → (심볼릭 링크 또는 복사됨)
- ✓ skills → (심볼릭 링크 또는 복사됨)
- ✓ settings.glocal.json → (심볼릭 링크 또는 복사됨)
- commands 개수, skills 개수

**참고:** 심볼릭 링크 방식은 ai-env에서 변경 시 자동 반영됨
