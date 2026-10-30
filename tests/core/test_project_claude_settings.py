"""ai-env 프로젝트 Claude 설정 계약.

ai-env는 `.claude/rules`가 글로벌 규칙의 원본이라 `~/.claude/rules` 배포본과 같은 내용이
두 번 로드된다. 프로젝트 설정의 `claudeMdExcludes`로 원본만 제외하고 배포본은 남긴다.
"""

from __future__ import annotations

import json
from fnmatch import fnmatch
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SETTINGS = _PROJECT_ROOT / ".claude" / "settings.json"


def test_rule_sources_are_excluded_but_deployed_rules_still_load() -> None:
    patterns = json.loads(_SETTINGS.read_text(encoding="utf-8"))["claudeMdExcludes"]
    source_rule = "/Users/megan/work/glasslego/ai-env/.claude/rules/shared-session-journal.md"
    deployed_rule = "/Users/megan/.claude/rules/shared-session-journal.md"
    project_memory = "/Users/megan/work/glasslego/ai-env/CLAUDE.md"
    assert any(fnmatch(source_rule, pattern) for pattern in patterns)
    # 배포된 글로벌 규칙과 프로젝트 CLAUDE.md는 계속 로드돼야 한다.
    assert not any(fnmatch(deployed_rule, pattern) for pattern in patterns)
    assert not any(fnmatch(project_memory, pattern) for pattern in patterns)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
