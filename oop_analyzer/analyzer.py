"""
Core OOP Analyzer engine.

This module provides the main analyzer class that orchestrates
the analysis process using configured rules.
"""

import ast
from pathlib import Path
from typing import Any

from .config import AnalyzerConfig
from .formatters import AnalysisReport, get_formatter
from .rules import RULE_REGISTRY, BaseRule, RuleResult
from .safety import SafetyValidator


class OOPAnalyzer:
    """
    Main analyzer class for checking OOP best practices.

    This class:
    1. Safely parses Python code (never executes it)
    2. Runs configured rules against the AST
    3. Aggregates results into a report
    4. Formats output in the requested format
    """

    def __init__(self, config: AnalyzerConfig | None = None):
        """
        Initialize the analyzer.

        Args:
            config: Configuration for the analyzer. Uses defaults if not provided.
        """
        self.config = config or AnalyzerConfig.default()
        self.safety = SafetyValidator(max_file_size=self.config.max_file_size)
        self._rules: dict[str, BaseRule] = {}
        self._initialize_rules()

    def _initialize_rules(self) -> None:
        """Initialize enabled rules based on configuration."""
        for rule_name in self.config.get_enabled_rules():
            if rule_name in RULE_REGISTRY:
                rule_config = self.config.rules.get(rule_name)
                options = rule_config.options if rule_config else {}
                self._rules[rule_name] = RULE_REGISTRY[rule_name](options)

    def analyze_source(self, source: str, file_path: str = "<string>") -> AnalysisReport:
        """
        Analyze Python source code string.

        Args:
            source: Python source code as a string
            file_path: Optional file path for reporting

        Returns:
            AnalysisReport with results from all enabled rules
        """
        errors: list[dict[str, Any]] = []
        results: dict[str, RuleResult] = {}

        # Validate source can be parsed
        safety_report = self.safety.validate_source_code(source, file_path)
        if not safety_report.is_safe:
            errors.append(
                {
                    "file": file_path,
                    "error": "Failed to parse source",
                    "details": safety_report.issues,
                }
            )
            return AnalysisReport(
                files_analyzed=[],
                results={},
                config=self.config.to_dict(),
                errors=errors,
            )

        # Parse the source
        tree = self.safety.parse_safely(source, file_path)
        if tree is None:
            errors.append(
                {
                    "file": file_path,
                    "error": "Failed to parse source",
                }
            )
            return AnalysisReport(
                files_analyzed=[],
                results={},
                config=self.config.to_dict(),
                errors=errors,
            )

        # Run each enabled rule
        for rule_name, rule in self._rules.items():
            try:
                result = rule.analyze(tree, source, file_path)
                results[rule_name] = result
            except Exception as e:
                errors.append(
                    {
                        "file": file_path,
                        "rule": rule_name,
                        "error": str(e),
                    }
                )

        return AnalysisReport(
            files_analyzed=[file_path],
            results=results,
            config=self.config.to_dict(),
            errors=errors,
        )

    def analyze_file(self, file_path: str | Path) -> AnalysisReport:
        """
        Analyze a single Python file.

        Args:
            file_path: Path to the Python file

        Returns:
            AnalysisReport with results from all enabled rules
        """
        path = Path(file_path)
        errors: list[dict[str, Any]] = []

        # Validate file
        safety_report = self.safety.validate_file_path(path)
        if not safety_report.is_safe:
            errors.append(
                {
                    "file": str(path),
                    "error": "File validation failed",
                    "details": safety_report.issues,
                }
            )
            return AnalysisReport(
                files_analyzed=[],
                results={},
                config=self.config.to_dict(),
                errors=errors,
            )

        # Read and analyze
        try:
            source = path.read_text(encoding="utf-8")
        except Exception as e:
            errors.append(
                {
                    "file": str(path),
                    "error": f"Failed to read file: {e}",
                }
            )
            return AnalysisReport(
                files_analyzed=[],
                results={},
                config=self.config.to_dict(),
                errors=errors,
            )

        return self.analyze_source(source, str(path))

    def analyze_directory(self, dir_path: str | Path) -> AnalysisReport:
        """
        Analyze all Python files in a directory.

        Args:
            dir_path: Path to the directory

        Returns:
            AnalysisReport with aggregated results from all files
        """
        path = Path(dir_path)
        errors: list[dict[str, Any]] = []
        all_files: list[str] = []
        parsed_files: list[tuple[ast.Module, str, str]] = []

        # Validate directory
        safety_report = self.safety.validate_directory(path)
        if not safety_report.is_safe:
            errors.append(
                {
                    "path": str(path),
                    "error": "Directory validation failed",
                    "details": safety_report.issues,
                }
            )
            return AnalysisReport(
                files_analyzed=[],
                results={},
                config=self.config.to_dict(),
                errors=errors,
            )

        # Collect Python files
        python_files = self.safety.collect_python_files(path)

        # Filter based on include/exclude patterns
        python_files = self._filter_files(python_files, path)

        # Parse all files
        for file_path in python_files:
            file_safety = self.safety.validate_file_path(file_path)
            if not file_safety.is_safe:
                errors.append(
                    {
                        "file": str(file_path),
                        "error": "File validation failed",
                        "details": file_safety.issues,
                    }
                )
                continue

            try:
                source = file_path.read_text(encoding="utf-8")
                tree = self.safety.parse_safely(source, str(file_path))
                if tree:
                    parsed_files.append((tree, source, str(file_path)))
                    all_files.append(str(file_path))
                else:
                    errors.append(
                        {
                            "file": str(file_path),
                            "error": "Failed to parse file",
                        }
                    )
            except Exception as e:
                errors.append(
                    {
                        "file": str(file_path),
                        "error": f"Failed to read file: {e}",
                    }
                )

        # Run rules that support multi-file analysis
        results: dict[str, RuleResult] = {}
        for rule_name, rule in self._rules.items():
            try:
                # Use analyze_multiple for rules that benefit from seeing all files
                result = rule.analyze_multiple(parsed_files)
                results[rule_name] = result
            except Exception as e:
                errors.append(
                    {
                        "rule": rule_name,
                        "error": str(e),
                    }
                )

        return AnalysisReport(
            files_analyzed=all_files,
            results=results,
            config=self.config.to_dict(),
            errors=errors,
        )

    def analyze_module(self, module_path: str | Path) -> AnalysisReport:
        """
        Analyze a Python module (directory with __init__.py).

        Args:
            module_path: Path to the module directory

        Returns:
            AnalysisReport with results
        """
        path = Path(module_path)

        # Check if it's a valid module
        init_file = path / "__init__.py"
        if not init_file.exists():
            return AnalysisReport(
                files_analyzed=[],
                results={},
                config=self.config.to_dict(),
                errors=[
                    {
                        "path": str(path),
                        "error": "Not a valid Python module (missing __init__.py)",
                    }
                ],
            )

        return self.analyze_directory(path)

    def analyze(self, path: str | Path) -> AnalysisReport:
        """
        Analyze a path (file, directory, or module).

        Automatically detects the type and calls the appropriate method.

        Args:
            path: Path to analyze

        Returns:
            AnalysisReport with results
        """
        path = Path(path)

        if path.is_file():
            return self.analyze_file(path)
        elif path.is_dir():
            # Check if it's a module
            if (path / "__init__.py").exists():
                return self.analyze_module(path)
            return self.analyze_directory(path)
        else:
            return AnalysisReport(
                files_analyzed=[],
                results={},
                config=self.config.to_dict(),
                errors=[
                    {
                        "path": str(path),
                        "error": "Path does not exist",
                    }
                ],
            )

    def format_report(self, report: AnalysisReport, format_name: str | None = None) -> str:
        """
        Format a report in the specified format.

        Args:
            report: The analysis report to format
            format_name: Output format (json, xml, html). Uses config default if not specified.

        Returns:
            Formatted string
        """
        format_name = format_name or self.config.output_format
        formatter_class = get_formatter(format_name)
        formatter = formatter_class()
        return formatter.format(report)

    def _filter_files(self, files: list[Path], base_path: Path) -> list[Path]:
        """Filter files based on include/exclude patterns."""
        import fnmatch

        filtered: list[Path] = []

        for file_path in files:
            try:
                relative = file_path.relative_to(base_path)
            except ValueError:
                relative = file_path

            rel_str = str(relative)

            # Check exclude patterns
            excluded = False
            for pattern in self.config.exclude_patterns:
                if fnmatch.fnmatch(rel_str, pattern):
                    excluded = True
                    break

            if excluded:
                continue

            # Check include patterns
            included = False
            for pattern in self.config.include_patterns:
                if fnmatch.fnmatch(file_path.name, pattern):
                    included = True
                    break

            if included:
                filtered.append(file_path)

        return filtered
