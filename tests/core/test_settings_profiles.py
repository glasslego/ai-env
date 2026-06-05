"""Claude Code enterprise/personal 프로필 템플릿 정합성 테스트.

`claude personal`(개인 Anthropic 로그인)과 `claude`/`claude enterprise`(회사 Bedrock)는
**로그인/백엔드 관련 설정만** 달라야 한다. permissions, hooks, mcpServers, 모델 메타데이터,
타임아웃 등 그 외 모든 동작은 동일하게 유지되어야 향후 drift를 막을 수 있다.

이 모듈은 두 템플릿이 정확히 그 계약을 지키는지 검증한다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# 두 템플릿 위치 (repo 루트 기준)
_GLOBAL_DIR = Path(__file__).resolve().parents[2] / ".claude" / "global"
_ENTERPRISE = _GLOBAL_DIR / "settings.json.template"
_PERSONAL = _GLOBAL_DIR / "settings.personal.json.template"

# personal에서만 제거되어야 하는 Bedrock 로그인/백엔드 env 키.
# (이 키들이 남으면 개인 OAuth 로그인이 회사 Bedrock으로 새어나간다)
BEDROCK_ONLY_ENV_KEYS = {
    "CLAUDE_CODE_USE_BEDROCK",
    "ANTHROPIC_BEDROCK_BASE_URL",
    "CLAUDE_CODE_SKIP_BEDROCK_AUTH",
    "AWS_PROFILE",
    "AWS_REGION",
}

# Bedrock 형식(global.anthropic.*) ↔ direct-API 형식 모델 ID 매핑.
# personal은 api.anthropic.com을 쓰므로 Bedrock ID를 쓰면 모델 resolve가 실패한다.
MODEL_ENV_KEYS = {
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "ANTHROPIC_CUSTOM_MODEL_OPTION",
}


@pytest.fixture()
def enterprise() -> dict:
    """Load the enterprise (Bedrock) settings template."""
    return json.loads(_ENTERPRISE.read_text())


@pytest.fixture()
def personal() -> dict:
    """Load the personal (direct Anthropic login) settings template."""
    return json.loads(_PERSONAL.read_text())


def test_personal_removes_exactly_bedrock_login_env_keys(enterprise, personal):
    """personal env는 enterprise에서 Bedrock 로그인 키만 정확히 제거한 집합이어야 한다."""
    ent_keys = set(enterprise["env"])
    per_keys = set(personal["env"])

    # personal에는 enterprise에 없는 새 키가 없어야 한다.
    assert per_keys - ent_keys == set(), "personal에 enterprise에 없는 env 키가 있음"
    # 제거된 키는 정확히 Bedrock 로그인 키 집합이어야 한다.
    assert ent_keys - per_keys == BEDROCK_ONLY_ENV_KEYS


def test_personal_drops_api_key_helper(enterprise, personal):
    """apiKeyHelper(게이트웨이 토큰)는 enterprise 전용이며 personal에는 없어야 한다."""
    assert "apiKeyHelper" in enterprise
    assert "apiKeyHelper" not in personal


def test_personal_model_ids_are_direct_api_form(personal):
    """personal 모델 ID는 Bedrock 접두사/suffix가 없는 direct-API 형식이어야 한다."""
    for key in MODEL_ENV_KEYS:
        value = personal["env"][key]
        assert not value.startswith("global.anthropic."), f"{key}에 Bedrock 접두사가 남음"
        assert "[1m]" not in value, f"{key}에 [1m] Bedrock suffix가 남음"
        assert ":" not in value, f"{key}에 -v1:0 류 Bedrock suffix가 남음"

    # top-level model도 동일하게 direct-API 형식이어야 한다.
    model = personal["model"]
    assert not model.startswith("global.anthropic.")
    assert "[1m]" not in model
    assert ":" not in model


def _base_version(model_id: str) -> str:
    """Bedrock/direct-API 형식 차이를 제거하고 모델 버전 토큰만 추출.

    "global.anthropic.claude-opus-4-7[1m]" / "claude-opus-4-7" → "claude-opus-4-7"
    "global.anthropic.claude-haiku-4-5-20251001-v1:0" → "claude-haiku-4-5-20251001"
    """
    name = model_id.split("global.anthropic.")[-1]
    name = name.split("[")[0]  # [1m] 제거
    name = name.split(":")[0]  # -v1:0 의 :0 제거
    return name.removesuffix("-v1")


def test_personal_sonnet_haiku_match_enterprise_base_version(enterprise, personal):
    """Sonnet/Haiku 버전은 두 프로필이 동일해야 한다(형식만 다름). 임의 모델 변경 방지."""
    for key in ("ANTHROPIC_DEFAULT_SONNET_MODEL", "ANTHROPIC_DEFAULT_HAIKU_MODEL"):
        assert _base_version(enterprise["env"][key]) == _base_version(
            personal["env"][key]
        ), f"{key} 모델 버전이 두 프로필 간 불일치"


def test_opus_versions_offered_are_same_set(enterprise, personal):
    """Opus는 default/custom 슬롯이 백엔드별로 스왑되지만, 제공되는 버전 집합은 동일해야 한다.

    enterprise(회사 Bedrock): default=Opus 4.7, custom=Opus 4.8 (Bedrock 기본이 4.7)
    personal(개인 API):       default=Opus 4.8, custom=Opus 4.7 (직접 API 최신이 4.8)
    어느 쪽이든 picker에 4.7과 4.8을 모두 노출하므로 버전 집합은 같아야 한다.
    """
    opus_keys = ("ANTHROPIC_DEFAULT_OPUS_MODEL", "ANTHROPIC_CUSTOM_MODEL_OPTION")
    ent_versions = {_base_version(enterprise["env"][k]) for k in opus_keys}
    per_versions = {_base_version(personal["env"][k]) for k in opus_keys}
    assert ent_versions == per_versions, "두 프로필이 노출하는 Opus 버전 집합이 다름"
    # 두 버전(4.7, 4.8)이 실제로 모두 존재하는지 확인 (한쪽으로 쏠리지 않음)
    assert len(per_versions) == 2

    # personal 기본은 최신(Opus 4.8), enterprise 기본은 Bedrock 기준(Opus 4.7)
    assert _base_version(personal["env"]["ANTHROPIC_DEFAULT_OPUS_MODEL"]) == "claude-opus-4-8"
    assert _base_version(enterprise["env"]["ANTHROPIC_DEFAULT_OPUS_MODEL"]) == "claude-opus-4-7"


def test_non_login_settings_are_identical(enterprise, personal):
    """로그인과 무관한 블록은 두 프로필이 완전히 동일해야 한다."""
    assert enterprise["permissions"] == personal["permissions"]
    assert enterprise["hooks"] == personal["hooks"]
    assert enterprise["mcpServers"] == personal["mcpServers"]
    assert (
        enterprise["skipDangerousModePermissionPrompt"]
        == personal["skipDangerousModePermissionPrompt"]
    )


def test_non_model_env_values_are_identical(enterprise, personal):
    """모델 메타데이터를 제외한 공통 env 값은 동일해야 한다(타임아웃/AUTO_MODE 등).

    Opus default/custom 슬롯은 백엔드별로 4.7↔4.8이 스왑되므로 그 ID와 부속
    메타데이터(_NAME/_DESCRIPTION/_SUPPORTED_CAPABILITIES)는 비교에서 제외한다.
    """
    # 스왑되는 opus 슬롯 + 모든 모델 ID 키의 부속 메타데이터를 제외한다.
    opus_prefixes = ("ANTHROPIC_DEFAULT_OPUS_MODEL", "ANTHROPIC_CUSTOM_MODEL_OPTION")
    shared = set(enterprise["env"]) & set(personal["env"])
    for key in shared:
        if key in MODEL_ENV_KEYS:
            continue
        if any(key.startswith(p) for p in opus_prefixes):
            continue  # 스왑된 opus 슬롯의 메타데이터는 달라도 정상
        assert enterprise["env"][key] == personal["env"][key], f"{key} 값이 두 프로필 간 불일치"
