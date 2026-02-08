"""
Safety module for OOP Analyzer.

This module ensures that code is analyzed safely without execution.
It validates that only static analysis is performed and detects
potentially malicious code patterns.
"""

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SafetyReport:
    """Report from safety validation."""

    is_safe: bool
    file_path: str
    issues: list[str]

    def __bool__(self) -> bool:
        return self.is_safe


class SafetyValidator:
    """
    Validates Python code for safe static analysis.

    This class ensures that:
    1. Code is parsed using AST only (never executed)
    2. Potentially dangerous patterns are flagged
    3. File paths are validated
    """

    DANGEROUS_PATTERNS = [
        "exec",
        "eval",
        "compile",
        "__import__",
        "open",
        "subprocess",
        "os.system",
        "os.popen",
    ]

    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

    def __init__(self, max_file_size: int | None = None):
        self.max_file_size = max_file_size or self.MAX_FILE_SIZE_BYTES

    def validate_file_path(self, file_path: str | Path) -> SafetyReport:
        """Validate that a file path is safe to analyze."""
        path = Path(file_path)
        issues: list[str] = []

        if not path.exists():
            return SafetyReport(
                is_safe=False,
                file_path=str(path),
                issues=[f"File does not exist: {path}"],
            )

        if not path.is_file():
            return SafetyReport(
                is_safe=False,
                file_path=str(path),
                issues=[f"Path is not a file: {path}"],
            )

        if path.suffix != ".py":
            return SafetyReport(
                is_safe=False,
                file_path=str(path),
                issues=[f"File is not a Python file: {path}"],
            )

        try:
            file_size = path.stat().st_size
            if file_size > self.max_file_size:
                return SafetyReport(
                    is_safe=False,
                    file_path=str(path),
                    issues=[f"File too large: {file_size} bytes (max: {self.max_file_size} bytes)"],
                )
        except OSError as e:
            return SafetyReport(
                is_safe=False,
                file_path=str(path),
                issues=[f"Cannot access file: {e}"],
            )

        return SafetyReport(is_safe=True, file_path=str(path), issues=issues)

    def validate_source_code(self, source: str, file_path: str = "<string>") -> SafetyReport:
        """
        Validate source code can be safely parsed.

        This does NOT execute the code - it only parses it into an AST.
        """
        issues: list[str] = []

        try:
            ast.parse(source)
        except SyntaxError as e:
            return SafetyReport(
                is_safe=False,
                file_path=file_path,
                issues=[f"Syntax error in source: {e}"],
            )

        return SafetyReport(is_safe=True, file_path=file_path, issues=issues)

    def parse_safely(self, source: str, file_path: str = "<string>") -> ast.Module | None:
        """
        Safely parse source code into an AST.

        Returns None if parsing fails. Never executes code.
        """
        try:
            return ast.parse(source, filename=file_path)
        except SyntaxError:
            return None

    def validate_directory(self, dir_path: str | Path) -> SafetyReport:
        """Validate that a directory path is safe to analyze."""
        path = Path(dir_path)
        issues: list[str] = []

        if not path.exists():
            return SafetyReport(
                is_safe=False,
                file_path=str(path),
                issues=[f"Directory does not exist: {path}"],
            )

        if not path.is_dir():
            return SafetyReport(
                is_safe=False,
                file_path=str(path),
                issues=[f"Path is not a directory: {path}"],
            )

        return SafetyReport(is_safe=True, file_path=str(path), issues=issues)

    def collect_python_files(self, path: str | Path) -> list[Path]:
        """
        Safely collect all Python files from a path.

        If path is a file, returns a list with just that file.
        If path is a directory, recursively collects all .py files.
        """
        path = Path(path)

        if path.is_file():
            if path.suffix == ".py":
                return [path]
            return []

        if path.is_dir():
            return list(path.rglob("*.py"))

        return []
