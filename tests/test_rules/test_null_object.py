"""
Tests for the null object rule.
"""

import ast

import pytest

from oop_analyzer.rules.null_object import NullObjectRule


class TestNullObjectRule:
    """Tests for NullObjectRule."""

    @pytest.fixture
    def rule(self) -> NullObjectRule:
        return NullObjectRule()

    def test_detects_none_comparison_is(self, rule: NullObjectRule):
        """Test detection of 'x is None' comparison."""
        source = """
def check(x):
    if x is None:
        return False
    return True
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        assert any("None" in v.message for v in result.violations)

    def test_detects_none_comparison_is_not(self, rule: NullObjectRule):
        """Test detection of 'x is not None' comparison."""
        source = """
def check(x):
    if x is not None:
        return x.value
    return "default"
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations

    def test_detects_none_comparison_equals(self, rule: NullObjectRule):
        """Test detection of 'x == None' comparison."""
        source = """
def check(x):
    if x == None:
        return False
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations

    def test_detects_return_none(self, rule: NullObjectRule):
        """Test detection of 'return None' statements."""
        source = """
def find_user(user_id):
    if user_id == 0:
        return None
    return User(user_id)
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        assert any("return None" in v.message for v in result.violations)

    def test_detects_optional_parameter(self, rule: NullObjectRule):
        """Test detection of parameters with None default."""
        source = """
def process(data=None):
    if data is None:
        data = []
    return data
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        assert any("parameter" in v.message.lower() for v in result.violations)

    def test_detects_ternary_none_check(self, rule: NullObjectRule):
        """Test detection of ternary None checks."""
        source = """
def get_value(x):
    return x if x is not None else "default"
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        assert any("ternary" in v.message.lower() for v in result.violations)

    def test_counts_none_patterns(self, rule: NullObjectRule):
        """Test counting of None patterns."""
        source = """
def process(data=None):
    if data is None:
        return None
    return data
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.summary["total_none_checks"] >= 1
        assert result.summary["return_none_count"] >= 1
        assert result.summary["optional_param_count"] >= 1

    def test_option_disable_return_none(self):
        """Test disabling return None check."""
        rule = NullObjectRule(options={"check_return_none": False})
        source = """
def find():
    return None
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert not any("return None" in v.message for v in result.violations)

    def test_option_disable_none_comparisons(self):
        """Test disabling None comparison check."""
        rule = NullObjectRule(options={"check_none_comparisons": False})
        source = """
def check(x):
    if x is None:
        pass
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        # Should not have comparison violations
        comparison_violations = [
            v
            for v in result.violations
            if "comparison" in v.message.lower() or "if statement" in v.message.lower()
        ]
        assert len(comparison_violations) == 0

    def test_option_disable_optional_params(self):
        """Test disabling optional parameter check."""
        rule = NullObjectRule(options={"check_optional_params": False})
        source = """
def process(data=None):
    pass
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert not any("parameter" in v.message.lower() for v in result.violations)

    def test_handles_async_functions(self, rule: NullObjectRule):
        """Test handling of async functions."""
        source = """
async def fetch(url=None):
    if url is None:
        return None
    return await get(url)
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations

    def test_handles_kwonly_args_with_none(self, rule: NullObjectRule):
        """Test handling of keyword-only args with None default."""
        source = """
def process(*, callback=None):
    if callback is not None:
        callback()
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations

    def test_violation_includes_function_context(self, rule: NullObjectRule):
        """Test that violations include function context."""
        source = """
def my_function():
    return None
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        violation = result.violations[0]
        assert "my_function" in violation.message or "my_function" in str(violation.metadata)

    def test_none_patterns_metadata(self, rule: NullObjectRule):
        """Test that none_patterns metadata is populated."""
        source = """
def check(x):
    if x is None:
        return None
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert "none_patterns" in result.metadata
        assert len(result.metadata["none_patterns"]) > 0
