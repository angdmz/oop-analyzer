"""
Tests for the reference exposure rule.
"""

import ast

import pytest

from oop_analyzer.rules.reference_exposure import ReferenceExposureRule


class TestReferenceExposureRule:
    """Tests for ReferenceExposureRule."""

    @pytest.fixture
    def rule(self) -> ReferenceExposureRule:
        return ReferenceExposureRule()

    def test_detects_direct_return_of_private_list(self, rule: ReferenceExposureRule):
        """Test detection of returning private list directly."""
        source = """
class Container:
    def __init__(self):
        self._items = []

    def get_items(self):
        return self._items
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        assert any("_items" in v.message for v in result.violations)

    def test_detects_property_exposing_list(self, rule: ReferenceExposureRule):
        """Test detection of property exposing internal list."""
        source = """
class Container:
    def __init__(self):
        self._data = []

    @property
    def data(self):
        return self._data
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations

    def test_detects_collection_by_name(self, rule: ReferenceExposureRule):
        """Test detection based on collection-like naming."""
        source = """
class UserManager:
    def __init__(self):
        self._users = []

    def get_users(self):
        return self._users
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations

    def test_suggestion_mentions_copy(self, rule: ReferenceExposureRule):
        """Test that suggestions mention copying."""
        source = """
class Container:
    def __init__(self):
        self._items = []

    def get_items(self):
        return self._items
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        if result.has_violations:
            assert any("copy" in v.suggestion.lower() for v in result.violations)

    def test_no_violation_for_immutable_return(self, rule: ReferenceExposureRule):
        """Test no violation when returning immutable types."""
        source = """
class Container:
    def __init__(self):
        self._name = "test"

    def get_name(self):
        return self._name
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        # _name doesn't look like a collection
        collection_violations = [
            v for v in result.violations if "collection" in v.metadata.get("exposure_type", "")
        ]
        assert len(collection_violations) == 0

    def test_detects_dict_exposure(self, rule: ReferenceExposureRule):
        """Test detection of dict exposure."""
        source = """
class Config:
    def __init__(self):
        self._settings = {}

    def get_settings(self):
        return self._settings
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations

    def test_option_disable_properties(self):
        """Test disabling property checking."""
        rule = ReferenceExposureRule(options={"check_properties": False})
        source = """
class Container:
    def __init__(self):
        self._items = []

    @property
    def items(self):
        return self._items
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        property_violations = [v for v in result.violations if v.metadata.get("is_property")]
        assert len(property_violations) == 0

    def test_option_disable_getters(self):
        """Test disabling getter checking."""
        rule = ReferenceExposureRule(options={"check_getters": False})
        source = """
class Container:
    def __init__(self):
        self._items = []

    def get_items(self):
        return self._items
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        getter_violations = [v for v in result.violations if not v.metadata.get("is_property")]
        assert len(getter_violations) == 0

    def test_counts_exposures(self, rule: ReferenceExposureRule):
        """Test counting of different exposure types."""
        source = """
class Container:
    def __init__(self):
        self._items = []
        self._data = {}

    @property
    def items(self):
        return self._items

    def get_data(self):
        return self._data
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert "property_exposures" in result.summary
        assert "getter_exposures" in result.summary

    def test_metadata_includes_class(self, rule: ReferenceExposureRule):
        """Test that metadata includes class name."""
        source = """
class MyClass:
    def __init__(self):
        self._items = []

    def get_items(self):
        return self._items
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        if result.has_violations:
            violation = result.violations[0]
            assert violation.metadata.get("class") == "MyClass"

    def test_no_violation_outside_class(self, rule: ReferenceExposureRule):
        """Test no violation for functions outside classes."""
        source = """
_global_items = []

def get_items():
    return _global_items
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        # Should not flag module-level functions
        assert not result.has_violations

    def test_detects_children_attribute(self, rule: ReferenceExposureRule):
        """Test detection of 'children' attribute exposure."""
        source = """
class TreeNode:
    def __init__(self):
        self._children = []

    def get_children(self):
        return self._children
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations

    def test_detects_cache_attribute(self, rule: ReferenceExposureRule):
        """Test detection of 'cache' attribute exposure."""
        source = """
class Service:
    def __init__(self):
        self._cache = {}

    def get_cache(self):
        return self._cache
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
