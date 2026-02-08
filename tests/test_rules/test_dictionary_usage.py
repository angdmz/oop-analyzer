"""
Tests for the dictionary usage rule.
"""

import ast

import pytest

from oop_analyzer.rules.dictionary_usage import DictionaryUsageRule


class TestDictionaryUsageRule:
    """Tests for DictionaryUsageRule."""

    @pytest.fixture
    def rule(self) -> DictionaryUsageRule:
        return DictionaryUsageRule()

    def test_detects_dict_return_with_fixed_keys(self, rule: DictionaryUsageRule):
        """Test detection of returning dict with fixed keys."""
        source = """
def get_user():
    return {"name": "John", "age": 30, "email": "john@example.com"}
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        assert any("dict literal" in v.message.lower() for v in result.violations)

    def test_detects_dict_type_hint_return(self, rule: DictionaryUsageRule):
        """Test detection of Dict return type hint."""
        source = """
def get_user_info() -> dict:
    return {"name": "John", "age": 30}
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        # Should detect either the type hint or the dict literal
        assert any(
            "dict type hint" in v.message.lower() or "dict literal" in v.message.lower()
            for v in result.violations
        )

    def test_detects_dict_param_type_hint(self, rule: DictionaryUsageRule):
        """Test detection of Dict parameter type hint."""
        source = """
def process_user(user: dict) -> None:
    print(user)
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        assert any("parameter" in v.message.lower() for v in result.violations)

    def test_detects_repeated_dict_key_access(self, rule: DictionaryUsageRule):
        """Test detection of repeated dict key access."""
        source = """
def process(data):
    name = data["name"]
    age = data["age"]
    email = data["email"]
    return f"{name} ({age}): {email}"
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        assert any("multiple string keys" in v.message.lower() for v in result.violations)

    def test_allows_api_boundary_functions(self, rule: DictionaryUsageRule):
        """Test that API boundary functions are allowed."""
        source = """
def parse_response(response):
    return {"status": "ok", "data": response}

def to_json():
    return {"key": "value", "other": "data"}

def from_api_data(data):
    return {"parsed": True, "result": data}
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        # API boundary functions should not be flagged
        assert not result.has_violations

    def test_allows_api_boundary_classes(self, rule: DictionaryUsageRule):
        """Test that methods in API boundary classes are allowed."""
        source = """
class ApiClient:
    def get_response(self):
        return {"status": "ok", "data": []}
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        # API class methods should not be flagged
        assert not result.has_violations

    def test_respects_min_dict_keys(self):
        """Test that min_dict_keys option is respected."""
        rule = DictionaryUsageRule(options={"min_dict_keys": 4})
        source = """
def get_user():
    return {"name": "John", "age": 30}
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        # Only 2 keys, threshold is 4
        dict_return_violations = [
            v for v in result.violations if v.metadata.get("pattern") == "dict_return"
        ]
        assert len(dict_return_violations) == 0

    def test_option_disable_return_dicts(self):
        """Test disabling return dict checking."""
        rule = DictionaryUsageRule(options={"check_return_dicts": False})
        source = """
def get_user():
    return {"name": "John", "age": 30, "email": "test@test.com"}
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        dict_return_violations = [
            v for v in result.violations if v.metadata.get("pattern") == "dict_return"
        ]
        assert len(dict_return_violations) == 0

    def test_option_disable_dict_params(self):
        """Test disabling dict param checking."""
        rule = DictionaryUsageRule(options={"check_dict_params": False})
        source = """
def process(data: dict) -> None:
    pass
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        param_violations = [
            v for v in result.violations if v.metadata.get("pattern") == "dict_param"
        ]
        assert len(param_violations) == 0

    def test_option_disable_dict_access(self):
        """Test disabling dict access checking."""
        rule = DictionaryUsageRule(options={"check_dict_access": False})
        source = """
def process(data):
    return data["a"] + data["b"] + data["c"]
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        access_violations = [
            v for v in result.violations if v.metadata.get("pattern") == "dict_access"
        ]
        assert len(access_violations) == 0

    def test_suggestion_mentions_dataclass(self, rule: DictionaryUsageRule):
        """Test that suggestions mention dataclass."""
        source = """
def get_user():
    return {"name": "John", "age": 30}
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        if result.has_violations:
            assert any("dataclass" in v.suggestion.lower() for v in result.violations)

    def test_detects_dict_literal_assignment(self, rule: DictionaryUsageRule):
        """Test detection of dict literal assignment."""
        source = """
def process():
    user = {"name": "John", "age": 30, "email": "test@test.com"}
    return user
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations

    def test_skips_kwargs_parameter(self, rule: DictionaryUsageRule):
        """Test that kwargs parameter is not flagged."""
        source = """
def process(kwargs: dict) -> None:
    pass
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        # kwargs should be skipped
        param_violations = [v for v in result.violations if v.metadata.get("parameter") == "kwargs"]
        assert len(param_violations) == 0

    def test_skips_config_parameter(self, rule: DictionaryUsageRule):
        """Test that config parameter is not flagged."""
        source = """
def setup(config: dict) -> None:
    pass
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        # config should be skipped
        param_violations = [v for v in result.violations if v.metadata.get("parameter") == "config"]
        assert len(param_violations) == 0

    def test_handles_async_functions(self, rule: DictionaryUsageRule):
        """Test handling of async functions."""
        source = """
async def fetch_user():
    return {"name": "John", "age": 30}
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations

    def test_counts_violations(self, rule: DictionaryUsageRule):
        """Test counting of different violation types."""
        source = """
def get_user() -> dict:
    return {"name": "John", "age": 30}

def process(data: dict):
    return data["a"] + data["b"] + data["c"]
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert "dict_return_violations" in result.summary
        assert "dict_param_violations" in result.summary
        assert "dict_access_violations" in result.summary

    def test_metadata_includes_keys(self, rule: DictionaryUsageRule):
        """Test that metadata includes dict keys."""
        source = """
def get_user():
    return {"name": "John", "age": 30}
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        if result.has_violations:
            violation = [v for v in result.violations if v.metadata.get("keys")][0]
            assert "name" in violation.metadata["keys"]
            assert "age" in violation.metadata["keys"]

    def test_single_key_dict_not_flagged(self, rule: DictionaryUsageRule):
        """Test that single key dicts are not flagged."""
        source = """
def get_status():
    return {"status": "ok"}
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        # Single key should not be flagged (min is 2)
        dict_return_violations = [
            v for v in result.violations if v.metadata.get("pattern") == "dict_return"
        ]
        assert len(dict_return_violations) == 0

    def test_option_disable_api_boundaries(self):
        """Test disabling API boundary allowance."""
        rule = DictionaryUsageRule(options={"allow_api_boundaries": False})
        source = """
def parse_response():
    return {"status": "ok", "data": []}
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        # Should be flagged even though it's "parse_response"
        assert result.has_violations
