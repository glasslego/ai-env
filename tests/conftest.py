# pytest configuration
# pythonpath = ["src"] is set in pyproject.toml [tool.pytest.ini_options]

import pytest
from ai_env.core.session_storage import _cached_git_output


@pytest.fixture(autouse=True)
def _clear_git_shape_cache() -> None:
    """테스트마다 git 저장소를 새로 만들므로 저장소 구조 캐시를 비운다."""
    _cached_git_output.cache_clear()
