"""
Tests for the coupling rule.
"""

import ast

import pytest

from oop_analyzer.rules.coupling import CouplingRule


class TestCouplingRule:
    """Tests for CouplingRule."""

    @pytest.fixture
    def rule(self) -> CouplingRule:
        return CouplingRule()

    def test_detects_imports(self, rule: CouplingRule):
        """Test detection of import statements."""
        source = """
import os
import sys
from pathlib import Path
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert "os" in result.metadata["imports"]
        assert "sys" in result.metadata["imports"]
        assert "pathlib" in result.metadata["imports"]

    def test_counts_total_imports(self, rule: CouplingRule):
        """Test counting of total imports."""
        source = """
import os
import sys
import json
from pathlib import Path
from typing import Any
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.summary["total_imports"] == 5

    def test_warns_on_high_import_count(self):
        """Test warning when import count exceeds threshold."""
        rule = CouplingRule(options={"max_imports_warning": 3})
        source = """
import os
import sys
import json
import logging
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert result.has_violations
        assert any("High coupling" in v.message for v in result.violations)

    def test_classifies_stdlib_imports(self, rule: CouplingRule):
        """Test classification of stdlib imports."""
        source = """
import os
import sys
import json
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        # Stdlib imports are now tracked separately from external
        assert len(result.metadata["stdlib_imports"]) == 3

    def test_classifies_relative_imports(self, rule: CouplingRule):
        """Test classification of relative imports."""
        source = """
from . import module_a
from ..utils import helper
from .subpackage import something
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        assert len(result.metadata["internal_imports"]) == 3

    def test_import_details_include_line_numbers(self, rule: CouplingRule):
        """Test that import details include line numbers."""
        source = """
import os
import sys
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        details = result.metadata["import_details"]
        assert len(details) == 2
        assert all("line" in d for d in details)

    def test_analyze_multiple_builds_dependency_graph(self, rule: CouplingRule):
        """Test that analyze_multiple builds a dependency graph."""
        source_a = """
import os
from .module_b import something
"""
        source_b = """
import json
"""
        tree_a = ast.parse(source_a)
        tree_b = ast.parse(source_b)

        files = [
            (tree_a, source_a, "module_a.py"),
            (tree_b, source_b, "module_b.py"),
        ]

        result = rule.analyze_multiple(files)

        assert "dependency_graph" in result.metadata
        assert "import_frequency" in result.metadata

    def test_analyze_multiple_counts_frequency(self, rule: CouplingRule):
        """Test that analyze_multiple counts import frequency."""
        source_a = """
import os
import json
"""
        source_b = """
import os
import logging
"""
        source_c = """
import os
"""
        tree_a = ast.parse(source_a)
        tree_b = ast.parse(source_b)
        tree_c = ast.parse(source_c)

        files = [
            (tree_a, source_a, "a.py"),
            (tree_b, source_b, "b.py"),
            (tree_c, source_c, "c.py"),
        ]

        result = rule.analyze_multiple(files)

        freq = result.metadata["import_frequency"]
        assert freq["os"] == 3
        assert freq["json"] == 1

    def test_most_used_modules_in_summary(self, rule: CouplingRule):
        """Test that summary includes most used modules."""
        source_a = "import os\nimport json"
        source_b = "import os\nimport logging"
        source_c = "import os"

        files = [
            (ast.parse(source_a), source_a, "a.py"),
            (ast.parse(source_b), source_b, "b.py"),
            (ast.parse(source_c), source_c, "c.py"),
        ]

        result = rule.analyze_multiple(files)

        assert "most_used_modules" in result.summary
        most_used = result.summary["most_used_modules"]
        assert most_used[0][0] == "os"  # os should be first

    def test_coupling_chains_detected(self, rule: CouplingRule):
        """Test detection of coupling chains."""
        source_a = "from .b import x"
        source_b = "from .c import y"
        source_c = "import os"

        files = [
            (ast.parse(source_a), source_a, "pkg/a.py"),
            (ast.parse(source_b), source_b, "pkg/b.py"),
            (ast.parse(source_c), source_c, "pkg/c.py"),
        ]

        result = rule.analyze_multiple(files)

        assert "coupling_chains" in result.metadata

    def test_handles_from_import_with_multiple_names(self, rule: CouplingRule):
        """Test handling of from imports with multiple names."""
        source = """
from typing import Any, List, Dict, Optional
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        details = result.metadata["import_details"]
        assert len(details) == 1
        assert "Any" in details[0]["names"]
        assert "List" in details[0]["names"]

    def test_no_violation_with_few_imports(self, rule: CouplingRule):
        """Test no violation with few imports."""
        source = """
import os
"""
        tree = ast.parse(source)
        result = rule.analyze(tree, source, "test.py")

        # Default threshold is 10, so 1 import should not trigger
        high_coupling_violations = [v for v in result.violations if "High coupling" in v.message]
        assert len(high_coupling_violations) == 0
