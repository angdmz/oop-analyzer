"""
Tests for the polymorphism rule.
"""

import ast

import pytest

from oop_analyzer.rules.polymorphism import PolymorphismRule


class TestPolymorphismRule:
    """Tests for PolymorphismRule."""

    @pytest.fixture
    def rule(self) -> PolymorphismRule:
        return PolymorphismRule()

    def test_detects_long_if_elif_chain(self, rule: PolymorphismRule):
        """Test detection of long if/elif chains."""
        source = """
def process(value):
    if value == "a":
        return 1
    elif value == "b":
        return 2
    elif value == "c":
        return 3
    elif value == "d":
        return 4
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        assert any("if/elif" in v.message.lower() for v in result.violations)

    def test_detects_isinstance_check(self, rule: PolymorphismRule):
        """Test detection of isinstance() checks."""
        source = """
def process(obj):
    if isinstance(obj, Dog):
        obj.bark()
    elif isinstance(obj, Cat):
        obj.meow()
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        assert any("isinstance" in v.message.lower() for v in result.violations)

    def test_detects_type_attribute_check(self, rule: PolymorphismRule):
        """Test detection of type/kind attribute checks."""
        source = """
def process(shape):
    if shape.type == "circle":
        return calculate_circle_area(shape)
    elif shape.type == "rectangle":
        return calculate_rectangle_area(shape)
    elif shape.type == "triangle":
        return calculate_triangle_area(shape)
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        assert any("type" in v.message.lower() for v in result.violations)

    def test_respects_min_branches_option(self):
        """Test that min_branches option is respected."""
        rule = PolymorphismRule(options={"min_branches": 5})
        source = """
def process(value):
    if value == "a":
        return 1
    elif value == "b":
        return 2
    elif value == "c":
        return 3
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        # Only 3 branches, threshold is 5
        long_chain_violations = [v for v in result.violations if "if/elif" in v.message.lower()]
        assert len(long_chain_violations) == 0

    def test_option_disable_isinstance_check(self):
        """Test disabling isinstance check."""
        rule = PolymorphismRule(options={"check_isinstance": False})
        source = """
def process(obj):
    if isinstance(obj, Dog):
        obj.bark()
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert not any("isinstance" in v.message.lower() for v in result.violations)

    def test_option_disable_type_attribute_check(self):
        """Test disabling type attribute check."""
        rule = PolymorphismRule(options={"check_type_attributes": False})
        source = """
def process(obj):
    if obj.type == "a":
        pass
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert not any(
            "type" in v.message.lower() and "attribute" in v.message.lower()
            for v in result.violations
        )

    def test_detects_kind_attribute(self, rule: PolymorphismRule):
        """Test detection of 'kind' attribute checks."""
        source = """
def process(animal):
    if animal.kind == "dog":
        return "woof"
    elif animal.kind == "cat":
        return "meow"
    elif animal.kind == "bird":
        return "chirp"
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations

    def test_detects_status_attribute(self, rule: PolymorphismRule):
        """Test detection of 'status' attribute checks."""
        source = """
def process(order):
    if order.status == "pending":
        handle_pending(order)
    elif order.status == "shipped":
        handle_shipped(order)
    elif order.status == "delivered":
        handle_delivered(order)
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations

    def test_counts_patterns(self, rule: PolymorphismRule):
        """Test counting of different patterns."""
        source = """
def process(obj):
    if isinstance(obj, Dog):
        pass

    if obj.type == "a":
        pass
    elif obj.type == "b":
        pass
    elif obj.type == "c":
        pass
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.summary["isinstance_checks"] >= 1
        assert result.summary["type_attribute_checks"] >= 1

    def test_handles_nested_isinstance(self, rule: PolymorphismRule):
        """Test handling of isinstance in boolean expressions."""
        source = """
def process(obj):
    if isinstance(obj, Dog) or isinstance(obj, Cat):
        obj.make_sound()
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations

    def test_violation_includes_context(self, rule: PolymorphismRule):
        """Test that violations include function/class context."""
        source = """
class Handler:
    def process(self, obj):
        if isinstance(obj, Dog):
            pass
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        violation = result.violations[0]
        assert "function" in violation.metadata or "class" in violation.metadata

    def test_short_if_not_flagged(self, rule: PolymorphismRule):
        """Test that short if statements are not flagged."""
        source = """
def process(value):
    if value == "a":
        return 1
    else:
        return 0
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        # Only 2 branches, default threshold is 3
        long_chain_violations = [v for v in result.violations if "if/elif" in v.message.lower()]
        assert len(long_chain_violations) == 0

    def test_patterns_metadata(self, rule: PolymorphismRule):
        """Test that patterns metadata is populated."""
        source = """
def process(obj):
    if isinstance(obj, Dog):
        pass
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert "patterns" in result.metadata
        assert len(result.metadata["patterns"]) > 0

    def test_handles_match_statement(self, rule: PolymorphismRule):
        """Test handling of match statements (Python 3.10+)."""
        source = """
def process(command):
    match command:
        case "start":
            start()
        case "stop":
            stop()
        case "pause":
            pause()
        case "resume":
            resume()
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        assert any("match" in v.message.lower() for v in result.violations)
