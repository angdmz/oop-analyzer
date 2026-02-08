"""
Tests for the safety module.
"""

from pathlib import Path

import pytest

from oop_analyzer.safety import SafetyReport, SafetyValidator


class TestSafetyValidator:
    """Tests for SafetyValidator class."""

    @pytest.fixture
    def validator(self) -> SafetyValidator:
        return SafetyValidator()

    def test_validate_existing_python_file(self, validator: SafetyValidator, temp_python_file):
        """Test validation of a valid Python file."""
        file_path = temp_python_file("print('hello')")
        report = validator.validate_file_path(file_path)

        assert report.is_safe is True
        assert report.file_path == str(file_path)
        assert len(report.issues) == 0

    def test_validate_nonexistent_file(self, validator: SafetyValidator):
        """Test validation of a non-existent file."""
        report = validator.validate_file_path("/nonexistent/path/file.py")

        assert report.is_safe is False
        assert "does not exist" in report.issues[0]

    def test_validate_non_python_file(self, validator: SafetyValidator, temp_dir: Path):
        """Test validation rejects non-Python files."""
        txt_file = temp_dir / "test.txt"
        txt_file.write_text("hello")

        report = validator.validate_file_path(txt_file)

        assert report.is_safe is False
        assert "not a Python file" in report.issues[0]

    def test_validate_directory_as_file(self, validator: SafetyValidator, temp_dir: Path):
        """Test validation rejects directories when expecting file."""
        report = validator.validate_file_path(temp_dir)

        assert report.is_safe is False
        assert "not a file" in report.issues[0]

    def test_validate_file_too_large(self, temp_dir: Path):
        """Test validation rejects files exceeding size limit."""
        validator = SafetyValidator(max_file_size=100)

        large_file = temp_dir / "large.py"
        large_file.write_text("x = 1\n" * 100)  # More than 100 bytes

        report = validator.validate_file_path(large_file)

        assert report.is_safe is False
        assert "too large" in report.issues[0]

    def test_validate_source_code_valid(self, validator: SafetyValidator):
        """Test validation of valid Python source code."""
        source = "def hello():\n    print('world')"
        report = validator.validate_source_code(source)

        assert report.is_safe is True
        assert len(report.issues) == 0

    def test_validate_source_code_syntax_error(self, validator: SafetyValidator):
        """Test validation catches syntax errors."""
        source = "def broken(\n    print('missing paren'"
        report = validator.validate_source_code(source)

        assert report.is_safe is False
        assert "Syntax error" in report.issues[0]

    def test_parse_safely_valid(self, validator: SafetyValidator):
        """Test safe parsing of valid code."""
        source = "x = 1 + 2"
        tree = validator.parse_safely(source)

        assert tree is not None
        assert hasattr(tree, "body")

    def test_parse_safely_invalid(self, validator: SafetyValidator):
        """Test safe parsing returns None for invalid code."""
        source = "x = ("
        tree = validator.parse_safely(source)

        assert tree is None

    def test_validate_directory_exists(self, validator: SafetyValidator, temp_dir: Path):
        """Test validation of existing directory."""
        report = validator.validate_directory(temp_dir)

        assert report.is_safe is True
        assert len(report.issues) == 0

    def test_validate_directory_nonexistent(self, validator: SafetyValidator):
        """Test validation of non-existent directory."""
        report = validator.validate_directory("/nonexistent/directory")

        assert report.is_safe is False
        assert "does not exist" in report.issues[0]

    def test_validate_file_as_directory(self, validator: SafetyValidator, temp_python_file):
        """Test validation rejects files when expecting directory."""
        file_path = temp_python_file("x = 1")
        report = validator.validate_directory(file_path)

        assert report.is_safe is False
        assert "not a directory" in report.issues[0]

    def test_collect_python_files_from_file(self, validator: SafetyValidator, temp_python_file):
        """Test collecting Python files from a single file path."""
        file_path = temp_python_file("x = 1")
        files = validator.collect_python_files(file_path)

        assert len(files) == 1
        assert files[0] == file_path

    def test_collect_python_files_from_directory(self, validator: SafetyValidator, temp_module):
        """Test collecting Python files from a directory."""
        module_path = temp_module(
            {
                "__init__.py": "",
                "module_a.py": "x = 1",
                "module_b.py": "y = 2",
                "subdir/module_c.py": "z = 3",
            }
        )

        files = validator.collect_python_files(module_path)

        assert len(files) == 4
        assert all(f.suffix == ".py" for f in files)

    def test_collect_python_files_ignores_non_python(
        self, validator: SafetyValidator, temp_dir: Path
    ):
        """Test that non-Python files are ignored."""
        (temp_dir / "script.py").write_text("x = 1")
        (temp_dir / "readme.txt").write_text("hello")
        (temp_dir / "data.json").write_text("{}")

        files = validator.collect_python_files(temp_dir)

        assert len(files) == 1
        assert files[0].name == "script.py"


class TestSafetyReport:
    """Tests for SafetyReport dataclass."""

    def test_bool_true_when_safe(self):
        """Test SafetyReport is truthy when safe."""
        report = SafetyReport(is_safe=True, file_path="test.py", issues=[])
        assert bool(report) is True

    def test_bool_false_when_unsafe(self):
        """Test SafetyReport is falsy when unsafe."""
        report = SafetyReport(is_safe=False, file_path="test.py", issues=["error"])
        assert bool(report) is False
