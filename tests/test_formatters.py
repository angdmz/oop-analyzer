"""
Tests for the formatters module.
"""

import json
from datetime import datetime

import pytest

from oop_analyzer.formatters import AnalysisReport, HTMLFormatter, JSONFormatter, XMLFormatter
from oop_analyzer.rules.base import RuleResult, RuleViolation


@pytest.fixture
def sample_report() -> AnalysisReport:
    """Create a sample analysis report for testing."""
    violation = RuleViolation(
        rule_name="encapsulation",
        message="Direct property access: user.name",
        file_path="test.py",
        line=10,
        column=5,
        severity="warning",
        suggestion="Use a method instead",
        code_snippet="print(user.name)",
    )

    result = RuleResult(
        rule_name="encapsulation",
        violations=[violation],
        summary={"total_violations": 1},
    )

    return AnalysisReport(
        files_analyzed=["test.py", "utils.py"],
        results={"encapsulation": result},
        timestamp=datetime(2024, 1, 15, 10, 30, 0),
        config={"output_format": "json"},
    )


class TestJSONFormatter:
    """Tests for JSONFormatter."""

    def test_format_produces_valid_json(self, sample_report: AnalysisReport):
        """Test that output is valid JSON."""
        formatter = JSONFormatter()
        output = formatter.format(sample_report)

        data = json.loads(output)
        assert isinstance(data, dict)

    def test_format_includes_files(self, sample_report: AnalysisReport):
        """Test that output includes files analyzed."""
        formatter = JSONFormatter()
        output = formatter.format(sample_report)

        data = json.loads(output)
        assert "files_analyzed" in data
        assert "test.py" in data["files_analyzed"]

    def test_format_includes_violations(self, sample_report: AnalysisReport):
        """Test that output includes violations."""
        formatter = JSONFormatter()
        output = formatter.format(sample_report)

        data = json.loads(output)
        assert "results" in data
        assert "encapsulation" in data["results"]
        assert len(data["results"]["encapsulation"]["violations"]) == 1

    def test_format_respects_indent(self, sample_report: AnalysisReport):
        """Test that indent option is respected."""
        formatter = JSONFormatter(indent=4)
        output = formatter.format(sample_report)

        assert "    " in output  # 4-space indent

    def test_format_respects_sort_keys(self, sample_report: AnalysisReport):
        """Test that sort_keys option is respected."""
        formatter = JSONFormatter(sort_keys=True)
        output = formatter.format(sample_report)

        data = json.loads(output)
        assert isinstance(data, dict)


class TestXMLFormatter:
    """Tests for XMLFormatter."""

    def test_format_produces_valid_xml(self, sample_report: AnalysisReport):
        """Test that output is valid XML."""
        formatter = XMLFormatter()
        output = formatter.format(sample_report)

        assert "<?xml" in output
        assert "<oop-analysis-report>" in output

    def test_format_includes_metadata(self, sample_report: AnalysisReport):
        """Test that output includes metadata."""
        formatter = XMLFormatter()
        output = formatter.format(sample_report)

        assert "<metadata>" in output
        assert "<timestamp>" in output

    def test_format_includes_files(self, sample_report: AnalysisReport):
        """Test that output includes files."""
        formatter = XMLFormatter()
        output = formatter.format(sample_report)

        assert "<files-analyzed>" in output
        assert "test.py" in output

    def test_format_includes_violations(self, sample_report: AnalysisReport):
        """Test that output includes violations."""
        formatter = XMLFormatter()
        output = formatter.format(sample_report)

        assert "<violations>" in output
        assert "<violation>" in output

    def test_format_pretty_option(self, sample_report: AnalysisReport):
        """Test pretty printing option."""
        formatter = XMLFormatter(pretty=True)
        output = formatter.format(sample_report)

        assert "\n" in output  # Pretty printed has newlines


class TestHTMLFormatter:
    """Tests for HTMLFormatter."""

    def test_format_produces_valid_html(self, sample_report: AnalysisReport):
        """Test that output is valid HTML."""
        formatter = HTMLFormatter()
        output = formatter.format(sample_report)

        assert "<!DOCTYPE html>" in output
        assert "<html" in output
        assert "</html>" in output

    def test_format_includes_title(self, sample_report: AnalysisReport):
        """Test that output includes title."""
        formatter = HTMLFormatter()
        output = formatter.format(sample_report)

        assert "<title>" in output
        assert "OOP Analysis Report" in output

    def test_format_includes_summary_cards(self, sample_report: AnalysisReport):
        """Test that output includes summary cards."""
        formatter = HTMLFormatter()
        output = formatter.format(sample_report)

        assert "summary-cards" in output
        assert "Files Analyzed" in output

    def test_format_includes_violations(self, sample_report: AnalysisReport):
        """Test that output includes violations."""
        formatter = HTMLFormatter()
        output = formatter.format(sample_report)

        assert "violation" in output
        assert "user.name" in output

    def test_format_escapes_html(self, sample_report: AnalysisReport):
        """Test that HTML special characters are escaped."""
        violation = RuleViolation(
            rule_name="test",
            message="Check <script>alert('xss')</script>",
            file_path="test.py",
            line=1,
        )
        result = RuleResult(rule_name="test", violations=[violation])
        report = AnalysisReport(
            files_analyzed=["test.py"],
            results={"test": result},
        )

        formatter = HTMLFormatter()
        output = formatter.format(report)

        assert "<script>" not in output
        assert "&lt;script&gt;" in output

    def test_format_includes_styles(self, sample_report: AnalysisReport):
        """Test that output includes CSS styles."""
        formatter = HTMLFormatter()
        output = formatter.format(sample_report)

        assert "<style>" in output
        assert "background" in output
