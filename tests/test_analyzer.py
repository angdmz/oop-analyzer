"""
Tests for the core analyzer module.
"""

from pathlib import Path

from oop_analyzer import AnalyzerConfig, OOPAnalyzer
from oop_analyzer.formatters import AnalysisReport


class TestOOPAnalyzer:
    """Tests for OOPAnalyzer class."""

    def test_analyze_source_valid_code(self, analyzer: OOPAnalyzer):
        """Test analyzing valid Python source code."""
        source = """
def hello():
    print("world")
"""
        report = analyzer.analyze_source(source)

        assert isinstance(report, AnalysisReport)
        assert len(report.files_analyzed) == 1
        assert len(report.errors) == 0

    def test_analyze_source_with_violations(self, analyzer: OOPAnalyzer):
        """Test analyzing code with violations."""
        source = """
def process(user):
    print(user.name)
"""
        report = analyzer.analyze_source(source)

        assert report.total_violations > 0

    def test_analyze_source_syntax_error(self, analyzer: OOPAnalyzer, malformed_code: str):
        """Test analyzing code with syntax errors."""
        report = analyzer.analyze_source(malformed_code)

        assert len(report.errors) > 0
        assert len(report.files_analyzed) == 0

    def test_analyze_source_empty(self, analyzer: OOPAnalyzer, empty_code: str):
        """Test analyzing empty code."""
        report = analyzer.analyze_source(empty_code)

        assert len(report.errors) == 0
        assert report.total_violations == 0

    def test_analyze_file(self, analyzer: OOPAnalyzer, temp_python_file):
        """Test analyzing a Python file."""
        file_path = temp_python_file("x = 1")
        report = analyzer.analyze_file(file_path)

        assert len(report.files_analyzed) == 1
        assert str(file_path) in report.files_analyzed

    def test_analyze_file_nonexistent(self, analyzer: OOPAnalyzer):
        """Test analyzing non-existent file."""
        report = analyzer.analyze_file("/nonexistent/file.py")

        assert len(report.errors) > 0
        assert len(report.files_analyzed) == 0

    def test_analyze_file_not_python(self, analyzer: OOPAnalyzer, temp_dir: Path):
        """Test analyzing non-Python file."""
        txt_file = temp_dir / "test.txt"
        txt_file.write_text("hello")

        report = analyzer.analyze_file(txt_file)

        assert len(report.errors) > 0

    def test_analyze_directory(self, analyzer: OOPAnalyzer, temp_module):
        """Test analyzing a directory."""
        module_path = temp_module(
            {
                "__init__.py": "",
                "module_a.py": "x = 1",
                "module_b.py": "y = 2",
            }
        )

        report = analyzer.analyze_directory(module_path)

        assert len(report.files_analyzed) >= 2

    def test_analyze_directory_nonexistent(self, analyzer: OOPAnalyzer):
        """Test analyzing non-existent directory."""
        report = analyzer.analyze_directory("/nonexistent/directory")

        assert len(report.errors) > 0

    def test_analyze_module(self, analyzer: OOPAnalyzer, temp_module):
        """Test analyzing a Python module."""
        module_path = temp_module(
            {
                "__init__.py": "from .core import main",
                "core.py": "def main(): pass",
            }
        )

        report = analyzer.analyze_module(module_path)

        assert len(report.files_analyzed) >= 1

    def test_analyze_module_without_init(self, analyzer: OOPAnalyzer, temp_dir: Path):
        """Test analyzing directory without __init__.py."""
        (temp_dir / "script.py").write_text("x = 1")

        report = analyzer.analyze_module(temp_dir)

        assert len(report.errors) > 0
        assert "missing __init__.py" in report.errors[0]["error"]

    def test_analyze_auto_detects_file(self, analyzer: OOPAnalyzer, temp_python_file):
        """Test that analyze() auto-detects file type."""
        file_path = temp_python_file("x = 1")
        report = analyzer.analyze(file_path)

        assert len(report.files_analyzed) == 1

    def test_analyze_auto_detects_directory(self, analyzer: OOPAnalyzer, temp_dir: Path):
        """Test that analyze() auto-detects directory type."""
        (temp_dir / "script.py").write_text("x = 1")
        report = analyzer.analyze(temp_dir)

        assert len(report.files_analyzed) >= 1

    def test_analyze_auto_detects_module(self, analyzer: OOPAnalyzer, temp_module):
        """Test that analyze() auto-detects module type."""
        module_path = temp_module(
            {
                "__init__.py": "",
                "core.py": "x = 1",
            }
        )
        report = analyzer.analyze(module_path)

        assert len(report.files_analyzed) >= 1

    def test_config_affects_rules(self, temp_python_file):
        """Test that configuration affects which rules run."""
        config = AnalyzerConfig()
        config.enable_only("encapsulation")
        analyzer = OOPAnalyzer(config)

        file_path = temp_python_file("x = 1")
        report = analyzer.analyze_file(file_path)

        assert "encapsulation" in report.results
        assert "coupling" not in report.results

    def test_format_report_json(self, analyzer: OOPAnalyzer):
        """Test formatting report as JSON."""
        report = analyzer.analyze_source("x = 1")
        output = analyzer.format_report(report, "json")

        assert output.startswith("{")
        assert "files_analyzed" in output

    def test_format_report_xml(self, analyzer: OOPAnalyzer):
        """Test formatting report as XML."""
        report = analyzer.analyze_source("x = 1")
        output = analyzer.format_report(report, "xml")

        assert "<?xml" in output
        assert "oop-analysis-report" in output

    def test_format_report_html(self, analyzer: OOPAnalyzer):
        """Test formatting report as HTML."""
        report = analyzer.analyze_source("x = 1")
        output = analyzer.format_report(report, "html")

        assert "<!DOCTYPE html>" in output
        assert "OOP Analysis Report" in output

    def test_format_report_uses_config_default(self):
        """Test that format_report uses config default format."""
        config = AnalyzerConfig()
        config.output_format = "xml"
        analyzer = OOPAnalyzer(config)

        report = analyzer.analyze_source("x = 1")
        output = analyzer.format_report(report)

        assert "<?xml" in output

    def test_exclude_patterns_work(self, temp_module):
        """Test that exclude patterns filter files."""
        module_path = temp_module(
            {
                "__init__.py": "",
                "core.py": "x = 1",
                "test_core.py": "y = 2",
            }
        )

        config = AnalyzerConfig()
        config.exclude_patterns = ["test_*.py"]
        analyzer = OOPAnalyzer(config)

        report = analyzer.analyze_directory(module_path)

        # test_core.py should be excluded
        assert not any("test_core.py" in f for f in report.files_analyzed)

    def test_report_contains_config(self, analyzer: OOPAnalyzer):
        """Test that report contains configuration used."""
        report = analyzer.analyze_source("x = 1")

        assert "rules" in report.config
        assert "output_format" in report.config


class TestAnalysisReport:
    """Tests for AnalysisReport class."""

    def test_total_violations(self, analyzer: OOPAnalyzer, encapsulation_violation_code: str):
        """Test total_violations property."""
        report = analyzer.analyze_source(encapsulation_violation_code)

        assert report.total_violations >= 0
        assert report.total_violations == sum(r.violation_count for r in report.results.values())

    def test_violations_by_severity(self, analyzer: OOPAnalyzer, encapsulation_violation_code: str):
        """Test violations_by_severity property."""
        report = analyzer.analyze_source(encapsulation_violation_code)

        by_severity = report.violations_by_severity
        assert "error" in by_severity
        assert "warning" in by_severity
        assert "info" in by_severity

    def test_rules_with_violations(self, analyzer: OOPAnalyzer, encapsulation_violation_code: str):
        """Test rules_with_violations property."""
        report = analyzer.analyze_source(encapsulation_violation_code)

        rules = report.rules_with_violations
        assert isinstance(rules, list)

    def test_to_dict(self, analyzer: OOPAnalyzer):
        """Test to_dict method."""
        report = analyzer.analyze_source("x = 1")
        data = report.to_dict()

        assert "files_analyzed" in data
        assert "total_violations" in data
        assert "timestamp" in data
        assert "results" in data


class TestIntegration:
    """Integration tests for complete analysis scenarios."""

    def test_clean_oop_code_minimal_violations(self, analyzer: OOPAnalyzer, clean_oop_code: str):
        """Test that well-designed OOP code has minimal violations."""
        report = analyzer.analyze_source(clean_oop_code)

        # Clean code should have few or no violations
        # (some rules like coupling might still find imports)
        encapsulation_violations = report.results.get("encapsulation")
        if encapsulation_violations:
            assert encapsulation_violations.violation_count == 0

    def test_violation_code_detected(
        self,
        analyzer: OOPAnalyzer,
        encapsulation_violation_code: str,
        null_object_violation_code: str,
        polymorphism_violation_code: str,
    ):
        """Test that violation code is properly detected."""
        # Test encapsulation
        report = analyzer.analyze_source(encapsulation_violation_code)
        assert report.results["encapsulation"].has_violations

        # Test null object
        report = analyzer.analyze_source(null_object_violation_code)
        assert report.results["null_object"].has_violations

        # Test polymorphism
        report = analyzer.analyze_source(polymorphism_violation_code)
        assert report.results["polymorphism"].has_violations

    def test_full_module_analysis(self, analyzer: OOPAnalyzer, temp_module):
        """Test analyzing a complete module with multiple files."""
        module_path = temp_module(
            {
                "__init__.py": "from .models import User",
                "models.py": """
class User:
    def __init__(self, name):
        self.name = name
""",
                "services.py": """
from .models import User

def get_user_name(user):
    return user.name
""",
                "utils.py": """
def helper(data=None):
    if data is None:
        return []
    return data
""",
            }
        )

        report = analyzer.analyze_module(module_path)

        assert len(report.files_analyzed) >= 3
        assert report.total_violations > 0

        # Check coupling detected imports
        coupling_result = report.results.get("coupling")
        if coupling_result:
            assert coupling_result.summary["total_files"] >= 3

    def test_subdirectory_analysis(self, analyzer: OOPAnalyzer, temp_module):
        """Test analyzing module with subdirectories."""
        module_path = temp_module(
            {
                "__init__.py": "",
                "core/__init__.py": "",
                "core/engine.py": "x = 1",
                "utils/__init__.py": "",
                "utils/helpers.py": "y = 2",
            }
        )

        report = analyzer.analyze_module(module_path)

        # Should find files in subdirectories
        assert len(report.files_analyzed) >= 4
