"""
Tests for the boolean flag rule.
"""

import ast

import pytest

from oop_analyzer.rules.boolean_flag import BooleanFlagRule


class TestBooleanFlagRule:
    """Tests for BooleanFlagRule."""

    @pytest.fixture
    def rule(self) -> BooleanFlagRule:
        return BooleanFlagRule()

    def test_detects_bool_param_in_conditional(self, rule: BooleanFlagRule):
        """Test detection of boolean parameter used in conditional."""
        source = """
def process(data, verbose: bool = False):
    if verbose:
        print("Processing...")
    return data
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        assert any("verbose" in v.message for v in result.violations)

    def test_detects_is_prefix_param(self, rule: BooleanFlagRule):
        """Test detection of is_ prefixed parameter."""
        source = """
def save(data, is_draft):
    if is_draft:
        save_draft(data)
    else:
        save_final(data)
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        assert any("is_draft" in v.message for v in result.violations)

    def test_detects_constructor_flag(self, rule: BooleanFlagRule):
        """Test detection of boolean flag in constructor."""
        source = """
class Service:
    def __init__(self, use_cache: bool = True):
        if use_cache:
            self._cache = {}
        else:
            self._cache = None
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        assert any("Constructor" in v.message for v in result.violations)

    def test_detects_method_flag(self, rule: BooleanFlagRule):
        """Test detection of boolean flag in method."""
        source = """
class Processor:
    def process(self, data, force: bool = False):
        if force:
            self._clear_cache()
        return self._process(data)
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        assert any("Method" in v.message for v in result.violations)

    def test_no_violation_without_conditional(self, rule: BooleanFlagRule):
        """Test no violation when bool param is not used in conditional."""
        source = """
def log(message, is_error: bool = False):
    return {"message": message, "is_error": is_error}
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        # No conditional usage, should not flag
        assert not result.has_violations

    def test_option_disable_constructors(self):
        """Test disabling constructor checking."""
        rule = BooleanFlagRule(options={"check_constructors": False})
        source = """
class Service:
    def __init__(self, enabled: bool = True):
        if enabled:
            self.start()
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert not result.has_violations

    def test_option_disable_methods(self):
        """Test disabling method checking."""
        rule = BooleanFlagRule(options={"check_methods": False})
        source = """
class Service:
    def process(self, force: bool = False):
        if force:
            self.clear()
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert not result.has_violations

    def test_option_disable_functions(self):
        """Test disabling function checking."""
        rule = BooleanFlagRule(options={"check_functions": False})
        source = """
def process(data, verbose: bool = False):
    if verbose:
        print(data)
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert not result.has_violations

    def test_suggestion_mentions_split(self, rule: BooleanFlagRule):
        """Test that suggestions mention splitting."""
        source = """
def process(data, verbose: bool = False):
    if verbose:
        print(data)
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        if result.has_violations:
            assert any("split" in v.suggestion.lower() for v in result.violations)

    def test_counts_violations(self, rule: BooleanFlagRule):
        """Test counting of different violation types."""
        source = """
class Service:
    def __init__(self, enabled: bool = True):
        if enabled:
            pass

    def process(self, force: bool = False):
        if force:
            pass

def helper(verbose: bool = False):
    if verbose:
        pass
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert "constructor_flags" in result.summary
        assert "method_flags" in result.summary
        assert "function_flags" in result.summary

    def test_detects_enable_prefix(self, rule: BooleanFlagRule):
        """Test detection of enable_ prefixed parameter."""
        source = """
def configure(enable_logging):
    if enable_logging:
        setup_logging()
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations

    def test_detects_boolean_default_true(self, rule: BooleanFlagRule):
        """Test detection of parameter with True default."""
        source = """
def process(data, validate=True):
    if validate:
        check(data)
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations

    def test_metadata_includes_usages(self, rule: BooleanFlagRule):
        """Test that metadata includes conditional usages count."""
        source = """
def process(data, verbose: bool = False):
    if verbose:
        print("start")
    if verbose:
        print("end")
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        if result.has_violations:
            violation = result.violations[0]
            assert violation.metadata.get("conditional_usages") >= 2

    def test_handles_async_functions(self, rule: BooleanFlagRule):
        """Test handling of async functions."""
        source = """
async def fetch(url, use_cache: bool = True):
    if use_cache:
        return await get_cached(url)
    return await fetch_fresh(url)
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
