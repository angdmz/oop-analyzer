"""
Tests for the type code rule.
"""

import ast

import pytest

from oop_analyzer.rules.type_code import TypeCodeRule


class TestTypeCodeRule:
    """Tests for TypeCodeRule."""

    @pytest.fixture
    def rule(self) -> TypeCodeRule:
        return TypeCodeRule()

    def test_detects_constant_type_code(self, rule: TypeCodeRule):
        """Test detection of type code with constants."""
        source = """
EUROPEAN = 1
AFRICAN = 2
NORWEGIAN_BLUE = 3

class Bird:
    def getSpeed(self):
        if self.type == EUROPEAN:
            return self.getBaseSpeed()
        elif self.type == AFRICAN:
            return self.getBaseSpeed() - self.getLoadFactor()
        elif self.type == NORWEGIAN_BLUE:
            return 0
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        assert any("type" in v.message.lower() for v in result.violations)

    def test_detects_enum_type_code(self, rule: TypeCodeRule):
        """Test detection of type code with enum values."""
        source = """
class BirdType:
    EUROPEAN = 1
    AFRICAN = 2

class Bird:
    def getSpeed(self):
        if self.type == BirdType.EUROPEAN:
            return 10
        elif self.type == BirdType.AFRICAN:
            return 20
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations

    def test_detects_status_attribute(self, rule: TypeCodeRule):
        """Test detection of status attribute checks."""
        source = """
class Order:
    def process(self):
        if self.status == "pending":
            self.prepare()
        elif self.status == "shipped":
            self.track()
        elif self.status == "delivered":
            self.complete()
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        assert any("status" in v.message.lower() for v in result.violations)

    def test_detects_kind_attribute(self, rule: TypeCodeRule):
        """Test detection of kind attribute checks."""
        source = """
class Shape:
    def area(self):
        if self.kind == CIRCLE:
            return 3.14 * self.r ** 2
        elif self.kind == RECTANGLE:
            return self.w * self.h
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations

    def test_respects_min_branches(self):
        """Test that min_branches option is respected."""
        rule = TypeCodeRule(options={"min_branches": 4})
        source = """
class Bird:
    def getSpeed(self):
        if self.type == EUROPEAN:
            return 10
        elif self.type == AFRICAN:
            return 20
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        # Only 2 branches, threshold is 4
        assert not result.has_violations

    def test_single_branch_not_flagged(self, rule: TypeCodeRule):
        """Test that single if statements are not flagged."""
        source = """
class Bird:
    def check(self):
        if self.type == EUROPEAN:
            return True
        return False
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        # Single branch should not be flagged
        type_code_violations = [v for v in result.violations if "type code" in v.message.lower()]
        assert len(type_code_violations) == 0

    def test_suggestion_mentions_polymorphism(self, rule: TypeCodeRule):
        """Test that suggestions mention polymorphism."""
        source = """
class Bird:
    def getSpeed(self):
        if self.type == EUROPEAN:
            return 10
        elif self.type == AFRICAN:
            return 20
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        if result.has_violations:
            assert any(
                "polymorphism" in v.suggestion.lower() or "subclass" in v.suggestion.lower()
                for v in result.violations
            )

    def test_detects_match_on_type(self, rule: TypeCodeRule):
        """Test detection of match statements on type attributes."""
        source = """
class Handler:
    def process(self):
        match self.type:
            case "a":
                return 1
            case "b":
                return 2
            case "c":
                return 3
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        assert any("match" in v.message.lower() for v in result.violations)

    def test_metadata_includes_values(self, rule: TypeCodeRule):
        """Test that metadata includes comparison values."""
        source = """
class Bird:
    def getSpeed(self):
        if self.type == EUROPEAN:
            return 10
        elif self.type == AFRICAN:
            return 20
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        if result.has_violations:
            violation = result.violations[0]
            assert (
                "comparison_values" in violation.metadata
                or "checked_attribute" in violation.metadata
            )

    def test_counts_patterns(self, rule: TypeCodeRule):
        """Test counting of different pattern types."""
        source = """
class Bird:
    def getSpeed(self):
        if self.type == EUROPEAN:
            return 10
        elif self.type == AFRICAN:
            return 20
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert "constant_comparisons" in result.summary or "type_attribute_checks" in result.summary

    def test_option_disable_constants(self):
        """Test disabling constant checking."""
        rule = TypeCodeRule(options={"check_constants": False})
        source = """
def process(value):
    if value == OPTION_A:
        return 1
    elif value == OPTION_B:
        return 2
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        # Without type attribute, and constants disabled, should not flag
        constant_violations = [
            v for v in result.violations if v.metadata.get("pattern_type") == "constant"
        ]
        assert len(constant_violations) == 0
