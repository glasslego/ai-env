"""SecretsManager 테스트 — export_to_shell() 이스케이핑 검증"""

from __future__ import annotations

from ai_env.core.secrets import SecretsManager


class TestExportToShell:
    """export_to_shell()의 특수문자 이스케이핑 테스트"""

    def _make_manager(self, cache: dict[str, str]) -> SecretsManager:
        """캐시를 직접 주입하여 .env 파일 없이 테스트"""
        sm = SecretsManager.__new__(SecretsManager)
        sm._cache = cache
        sm.env_file = "test.env"
        return sm

    def test_simple_value_no_quotes(self):
        sm = self._make_manager({"API_KEY": "sk-abc123"})
        result = sm.export_to_shell()
        assert "export API_KEY=sk-abc123" in result

    def test_value_with_spaces(self):
        sm = self._make_manager({"NAME": "hello world"})
        result = sm.export_to_shell()
        assert "export NAME='hello world'" in result

    def test_value_with_dollar_sign(self):
        sm = self._make_manager({"VAL": "price$100"})
        result = sm.export_to_shell()
        assert "export VAL='price$100'" in result

    def test_value_with_double_quotes(self):
        sm = self._make_manager({"VAL": 'say "hello"'})
        result = sm.export_to_shell()
        assert "export VAL='say \"hello\"'" in result

    def test_value_with_single_quotes(self):
        """작은따옴표는 '\\'' 패턴으로 이스케이핑"""
        sm = self._make_manager({"VAL": "it's a test"})
        result = sm.export_to_shell()
        assert "export VAL='it'\\''s a test'" in result

    def test_value_with_backslash(self):
        sm = self._make_manager({"PATH": "C:\\Users\\test"})
        result = sm.export_to_shell()
        assert "export PATH='C:\\Users\\test'" in result

    def test_value_with_backtick(self):
        sm = self._make_manager({"CMD": "echo `whoami`"})
        result = sm.export_to_shell()
        assert "export CMD='echo `whoami`'" in result

    def test_value_with_exclamation(self):
        sm = self._make_manager({"MSG": "hello!"})
        result = sm.export_to_shell()
        assert "export MSG='hello!'" in result

    def test_comment_keys_skipped(self):
        sm = self._make_manager({"#comment": "ignored", "REAL": "value"})
        result = sm.export_to_shell()
        assert "#comment" not in result.split("\n")[-1]
        assert "export REAL=value" in result

    def test_empty_values_skipped(self):
        sm = self._make_manager({"EMPTY": ""})
        result = sm.export_to_shell()
        assert "EMPTY" not in result.split("Source:")[-1]

    def test_mixed_special_chars(self):
        """여러 특수문자가 섞인 복합 케이스"""
        sm = self._make_manager({"COMPLEX": "pa$$w0rd'with\"special chars"})
        result = sm.export_to_shell()
        # 작은따옴표로 감싸고, 내부 작은따옴표만 이스케이핑
        assert "export COMPLEX='pa$$w0rd'\\''with\"special chars'" in result
