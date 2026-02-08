"""
Tests for the functions_to_objects rule.
"""

import ast

import pytest

from oop_analyzer.rules.functions_to_objects import FunctionsToObjectsRule


class TestFunctionsToObjectsRule:
    """Tests for FunctionsToObjectsRule."""

    @pytest.fixture
    def rule(self) -> FunctionsToObjectsRule:
        return FunctionsToObjectsRule()

    def test_detects_function_with_many_params(self, rule: FunctionsToObjectsRule):
        """Test detection of functions with many parameters."""
        source = """
def create_user(name, email, age, address, phone):
    return {"name": name, "email": email}
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        assert any("parameter" in v.message.lower() for v in result.violations)

    def test_respects_max_params_option(self):
        """Test that max_params option is respected."""
        rule = FunctionsToObjectsRule(options={"max_params": 6})
        source = """
def create_user(name, email, age, address, phone):
    pass
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        # 5 params, threshold is 6
        param_violations = [v for v in result.violations if "parameter" in v.message.lower()]
        assert len(param_violations) == 0

    def test_detects_dict_return(self, rule: FunctionsToObjectsRule):
        """Test detection of functions returning dictionaries."""
        source = """
def get_user_info():
    return {"name": "John", "age": 30}
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        assert any("dictionary" in v.message.lower() for v in result.violations)

    def test_detects_dict_call_return(self, rule: FunctionsToObjectsRule):
        """Test detection of functions returning dict() call."""
        source = """
def get_config():
    return dict(host="localhost", port=8080)
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        assert any("dictionary" in v.message.lower() for v in result.violations)

    def test_option_disable_dict_returns(self):
        """Test disabling dict return check."""
        rule = FunctionsToObjectsRule(options={"check_dict_returns": False})
        source = """
def get_info():
    return {"key": "value"}
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert not any("dictionary" in v.message.lower() for v in result.violations)

    def test_detects_related_functions(self, rule: FunctionsToObjectsRule):
        """Test detection of related functions with common prefix."""
        source = """
def user_create(name):
    pass

def user_update(user, name):
    pass

def user_delete(user):
    pass

def user_validate(user):
    pass
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        assert any("related" in v.message.lower() for v in result.violations)

    def test_option_disable_related_functions(self):
        """Test disabling related functions check."""
        rule = FunctionsToObjectsRule(options={"check_related_functions": False})
        source = """
def user_create(name):
    pass

def user_update(user):
    pass

def user_delete(user):
    pass
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert not any("related" in v.message.lower() for v in result.violations)

    def test_ignores_methods_in_classes(self, rule: FunctionsToObjectsRule):
        """Test that methods inside classes are ignored."""
        source = """
class User:
    def create(self, name, email, age, address, phone):
        pass
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        # Methods should not be flagged
        param_violations = [v for v in result.violations if "parameter" in v.message.lower()]
        assert len(param_violations) == 0

    def test_ignores_private_functions(self, rule: FunctionsToObjectsRule):
        """Test that private functions are not flagged for params."""
        source = """
def _internal_helper(a, b, c, d, e, f):
    pass
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        # Private functions should not be flagged
        param_violations = [v for v in result.violations if "parameter" in v.message.lower()]
        assert len(param_violations) == 0

    def test_handles_async_functions(self, rule: FunctionsToObjectsRule):
        """Test handling of async functions."""
        source = """
async def fetch_data(url, headers, params, timeout, retries):
    pass
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations

    def test_counts_functions(self, rule: FunctionsToObjectsRule):
        """Test counting of functions."""
        source = """
def func_a():
    pass

def func_b():
    pass

def func_c():
    pass
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.summary["total_functions"] == 3

    def test_function_groups_in_metadata(self, rule: FunctionsToObjectsRule):
        """Test that function groups are in metadata."""
        source = """
def order_create():
    pass

def order_update():
    pass

def order_delete():
    pass
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert "function_groups" in result.metadata
        groups = result.metadata["function_groups"]
        assert "order" in groups

    def test_short_prefix_not_grouped(self, rule: FunctionsToObjectsRule):
        """Test that short prefixes are not grouped."""
        source = """
def do_a():
    pass

def do_b():
    pass

def do_c():
    pass
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        # "do" is only 2 chars, should not be grouped
        groups = result.metadata["function_groups"]
        assert "do" not in groups

    def test_two_related_functions_not_flagged(self, rule: FunctionsToObjectsRule):
        """Test that only 2 related functions don't trigger violation."""
        source = """
def user_create():
    pass

def user_delete():
    pass
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        # Need 3+ related functions to trigger
        related_violations = [v for v in result.violations if "related" in v.message.lower()]
        assert len(related_violations) == 0

    def test_counts_varargs_and_kwargs(self, rule: FunctionsToObjectsRule):
        """Test that *args and **kwargs are counted as parameters."""
        source = """
def flexible(a, b, *args, **kwargs):
    pass
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        # a, b, *args, **kwargs = 4 params
        func_info = result.metadata["functions"][0]
        assert func_info["params"] == 4
