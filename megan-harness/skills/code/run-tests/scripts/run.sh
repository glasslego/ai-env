#!/usr/bin/env bash
# run-tests — 프로젝트 표준 테스트 명령을 자동 인식해 실행.

set -euo pipefail

CMD=""
CHANGED=0
EXTRA=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --cmd) CMD="$2"; shift 2;;
        --changed) CHANGED=1; shift;;
        -h|--help) sed -n '2,30p' "$0"; exit 0;;
        *) EXTRA+=("$1"); shift;;
    esac
done

if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
    echo "not a git repo — run from a project directory." >&2
    exit 2
fi
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

# 1) project-profile.yaml 의 test_cmd
if [[ -z "$CMD" && -f ".claude/project-profile.yaml" ]]; then
    PROFILE_CMD="$(grep -E '^test_cmd:' .claude/project-profile.yaml 2>/dev/null \
        | head -1 | sed -E 's/^test_cmd:[[:space:]]*//; s/^["'"'"']//; s/["'"'"']$//')"
    [[ -n "$PROFILE_CMD" ]] && CMD="$PROFILE_CMD"
fi

# 2) 자동 추론
if [[ -z "$CMD" ]]; then
    if [[ -f "pyproject.toml" ]]; then
        if grep -qE '(^\[tool\.pytest|pytest)' pyproject.toml; then
            CMD="uv run pytest"
        else
            CMD="uv run python -m unittest"
        fi
    elif [[ -f "package.json" ]] && grep -q '"test"' package.json; then
        CMD="npm test"
    elif [[ -f "Cargo.toml" ]]; then
        CMD="cargo test"
    elif [[ -f "go.mod" ]]; then
        CMD="go test ./..."
    fi
fi

if [[ -z "$CMD" ]]; then
    echo "could not determine test command. pass --cmd '<your command>' or set test_cmd in .claude/project-profile.yaml" >&2
    exit 2
fi

# --changed: pytest 일 때만 의미있게 처리
if [[ $CHANGED -eq 1 && "$CMD" == *pytest* ]]; then
    BASE="$(git merge-base HEAD origin/HEAD 2>/dev/null || git merge-base HEAD origin/main 2>/dev/null || echo HEAD~10)"
    FILES=()
    while IFS= read -r f; do
        [[ "$f" =~ test_.*\.py$|.*_test\.py$ ]] && FILES+=("$f")
    done < <(git diff --name-only "$BASE"..HEAD 2>/dev/null || true)
    if [[ ${#FILES[@]} -gt 0 ]]; then
        EXTRA=("${FILES[@]}" "${EXTRA[@]}")
    else
        echo "(no changed test files; running full suite)" >&2
    fi
fi

echo "+ $CMD ${EXTRA[*]:-}" >&2
exec $CMD "${EXTRA[@]:-}"
