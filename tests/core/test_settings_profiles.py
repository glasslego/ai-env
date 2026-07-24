"""Claude Code team/personal 프로필 템플릿 정합성 테스트.

`claude`/`claude team`은 팀 플랜 OAuth 로그인을 쓰는 기본 `~/.claude` 프로필이고,
`claude personal`은 별도 `CLAUDE_CONFIG_DIR=~/.claude-personal`로 로그인 상태만 분리한다.
두 settings 템플릿 모두 Bedrock/AWS 백엔드 설정을 포함하면 안 된다.

이 모듈은 두 템플릿이 정확히 그 계약을 지키는지 검증한다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_GLOBAL_DIR = Path(__file__).resolve().parents[2] / ".claude" / "global"
_TEAM = _GLOBAL_DIR / "settings.json.template"
_PERSONAL = _GLOBAL_DIR / "settings.personal.json.template"

BEDROCK_BACKEND_ENV_KEYS = {
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_SKIP_BEDROCK_AUTH",
    "ANTHROPIC_BEDROCK_BASE_URL",
    "AWS_PROFILE",
    "AWS_REGION",
}

MODEL_ENV_KEYS = {
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "ANTHROPIC_CUSTOM_MODEL_OPTION",
}


@pytest.fixture()
def team() -> dict:
    """Load the team-plan settings template."""
    return json.loads(_TEAM.read_text())


@pytest.fixture()
def personal() -> dict:
    """Load the personal (direct Anthropic login) settings template."""
    return json.loads(_PERSONAL.read_text())


def _assert_no_bedrock_backend(settings: dict, label: str) -> None:
    """Assert that a Claude settings template uses direct OAuth login."""
    assert "apiKeyHelper" not in settings, f"{label}에 apiKeyHelper가 남음"

    env = settings["env"]
    for key in BEDROCK_BACKEND_ENV_KEYS:
        assert key not in env, f"{label} env에 {key}가 남음"


def _assert_direct_model_ids(settings: dict, label: str) -> None:
    """Assert that model IDs are direct Claude Code model identifiers."""
    for key in MODEL_ENV_KEYS:
        value = settings["env"][key]
        assert not value.startswith("global.anthropic."), f"{key}에 Bedrock 접두사가 남음"
        assert "[1m]" not in value, f"{key}에 [1m] Bedrock suffix가 남음"
        assert ":" not in value, f"{key}에 -v1:0 류 Bedrock suffix가 남음"

    model = settings["model"]
    assert not model.startswith(
        "global.anthropic."
    ), f"{label} top-level model에 Bedrock 접두사가 남음"
    assert "[1m]" not in model, f"{label} top-level model에 [1m] Bedrock suffix가 남음"
    assert ":" not in model, f"{label} top-level model에 -v1:0 류 Bedrock suffix가 남음"


def test_team_and_personal_have_no_bedrock_backend_settings(team, personal):
    """team/personal 템플릿 모두 Bedrock/AWS 백엔드 설정을 포함하지 않아야 한다."""
    _assert_no_bedrock_backend(team, "team")
    _assert_no_bedrock_backend(personal, "personal")


def test_team_and_personal_model_ids_are_direct_api_form(team, personal):
    """team/personal 모델 ID는 direct Claude Code 형식이어야 한다."""
    _assert_direct_model_ids(team, "team")
    _assert_direct_model_ids(personal, "personal")


def test_team_and_personal_settings_are_identical(team, personal):
    """로그인 상태는 config dir로만 분리하므로 settings 템플릿 내용은 동일해야 한다."""
    assert team == personal


def test_mcp_servers_are_not_embedded(team, personal):
    """MCP 서버 정의는 settings.json 이 아니라 ~/.claude.json user scope 에 기록한다."""
    assert "mcpServers" not in team
    assert "mcpServers" not in personal
