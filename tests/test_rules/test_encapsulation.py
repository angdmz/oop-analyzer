"""
Tests for the encapsulation rule.
"""

import ast

import pytest

from oop_analyzer.rules.encapsulation import EncapsulationRule


class TestEncapsulationRule:
    """Tests for EncapsulationRule."""

    @pytest.fixture
    def rule(self) -> EncapsulationRule:
        return EncapsulationRule()

    def test_detects_direct_property_access(self, rule: EncapsulationRule):
        """Test detection of direct property access."""
        source = """
def process(user):
    print(user.name)
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        assert any("user.name" in v.message for v in result.violations)

    def test_allows_method_calls(self, rule: EncapsulationRule):
        """Test that method calls are not flagged."""
        source = """
def process(user):
    user.greet()
    user.get_name()
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        # Method calls should not be violations
        assert not any("greet" in v.message for v in result.violations)
        assert not any("get_name" in v.message for v in result.violations)

    def test_allows_self_access_by_default(self, rule: EncapsulationRule):
        """Test that self.x access is allowed by default."""
        source = """
class User:
    def get_name(self):
        return self.name
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert not any("self.name" in v.message for v in result.violations)

    def test_detects_self_access_when_disabled(self):
        """Test detection of self access when option is disabled."""
        rule = EncapsulationRule(options={"allow_self_access": False})
        source = """
class User:
    def get_name(self):
        return self.name
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        assert any("self.name" in v.message for v in result.violations)

    def test_detects_chained_access(self, rule: EncapsulationRule):
        """Test detection of chained property access."""
        source = """
def process(user):
    print(user.address.city)
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        violations = [v for v in result.violations if "chain" in v.message.lower()]
        assert len(violations) > 0

    def test_allows_dunder_access_by_default(self, rule: EncapsulationRule):
        """Test that dunder attributes are allowed by default."""
        source = """
def process(obj):
    print(obj.__class__)
    print(obj.__dict__)
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert not any("__class__" in v.message for v in result.violations)
        assert not any("__dict__" in v.message for v in result.violations)

    def test_allows_module_constants(self, rule: EncapsulationRule):
        """Test that module constants (all caps) are allowed."""
        source = """
import os
print(os.PATH_MAX)
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert not any("PATH_MAX" in v.message for v in result.violations)

    def test_allows_stdlib_module_access(self, rule: EncapsulationRule):
        """Test that stdlib module access is allowed."""
        source = """
import os
import sys
print(os.path)
print(sys.version)
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        # os and sys are in the allowed list
        assert not any("os.path" in v.message for v in result.violations)

    def test_violation_metadata(self, rule: EncapsulationRule):
        """Test that violations include proper metadata."""
        source = """
def process(user):
    print(user.name)
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        violation = result.violations[0]

        assert violation.rule_name == "encapsulation"
        assert violation.file_path == "test.py"
        assert violation.line > 0
        assert "base_object" in violation.metadata
        assert "accessed_attributes" in violation.metadata

    def test_max_chain_length_option(self):
        """Test max_chain_length option."""
        rule = EncapsulationRule(options={"max_chain_length": 1})
        source = """
def process(user):
    print(user.address)
    print(user.address.city)
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        # user.address has length 1 (allowed with max_chain_length=1)
        # user.address.city has length 2 (exceeds max_chain_length=1)
        chain_violations = [v for v in result.violations if "chain" in v.message.lower()]
        assert len(chain_violations) >= 1

    def test_summary_contains_count(self, rule: EncapsulationRule):
        """Test that result summary contains violation count."""
        source = """
def process(user):
    print(user.name)
    print(user.age)
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert "total_violations" in result.summary
        assert result.summary["total_violations"] == result.violation_count
