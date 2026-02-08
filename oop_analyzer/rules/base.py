"""
Base classes for OOP Analyzer rules.

All rules must inherit from BaseRule and implement the analyze method.
"""

import ast
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RuleViolation:
    """
    Represents a single rule violation found in the code.

    Attributes:
        rule_name: Name of the rule that was violated
        message: Human-readable description of the violation
        file_path: Path to the file containing the violation
        line: Line number where the violation occurs
        column: Column number where the violation occurs
        severity: Severity level ("error", "warning", "info")
        suggestion: Optional suggestion for fixing the violation
        code_snippet: Optional code snippet showing the violation
        metadata: Additional rule-specific metadata
    """

    rule_name: str
    message: str
    file_path: str
    line: int
    column: int = 0
    severity: str = "warning"
    suggestion: str | None = None
    code_snippet: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert violation to dictionary."""
        return {
            "rule_name": self.rule_name,
            "message": self.message,
            "file_path": self.file_path,
            "line": self.line,
            "column": self.column,
            "severity": self.severity,
            "suggestion": self.suggestion,
            "code_snippet": self.code_snippet,
            "metadata": self.metadata,
        }


@dataclass
class RuleResult:
    """
    Result of running a rule on code.

    Attributes:
        rule_name: Name of the rule
        violations: List of violations found
        summary: Summary statistics or information
        metadata: Additional rule-specific data (e.g., dependency graph)
    """

    rule_name: str
    violations: list[RuleViolation] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def violation_count(self) -> int:
        """Get the number of violations."""
        return len(self.violations)

    @property
    def has_violations(self) -> bool:
        """Check if there are any violations."""
        return len(self.violations) > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "rule_name": self.rule_name,
            "violation_count": self.violation_count,
            "violations": [v.to_dict() for v in self.violations],
            "summary": self.summary,
            "metadata": self.metadata,
        }


class BaseRule(ABC):
    """
    Abstract base class for all OOP analysis rules.

    To create a new rule:
    1. Inherit from BaseRule
    2. Set the class attributes (name, description, etc.)
    3. Implement the analyze method
    """

    name: str = "base_rule"
    description: str = "Base rule description"
    severity: str = "warning"

    def __init__(self, options: dict[str, Any] | None = None):
        """
        Initialize the rule with optional configuration.

        Args:
            options: Rule-specific configuration options
        """
        self.options = options or {}

    @abstractmethod
    def analyze(
        self,
        tree: ast.Module,
        source: str,
        file_path: str,
    ) -> RuleResult:
        """
        Analyze an AST and return violations.

        Args:
            tree: The parsed AST of the source code
            source: The original source code string
            file_path: Path to the file being analyzed

        Returns:
            RuleResult containing any violations found
        """
        pass

    def analyze_multiple(
        self,
        files: list[tuple[ast.Module, str, str]],
    ) -> RuleResult:
        """
        Analyze multiple files together.

        Some rules (like coupling) need to see all files at once.
        Default implementation just aggregates individual results.

        Args:
            files: List of (tree, source, file_path) tuples

        Returns:
            Combined RuleResult
        """
        all_violations: list[RuleViolation] = []
        combined_summary: dict[str, Any] = {}
        combined_metadata: dict[str, Any] = {}

        for tree, source, file_path in files:
            result = self.analyze(tree, source, file_path)
            all_violations.extend(result.violations)
            combined_summary.update(result.summary)
            combined_metadata.update(result.metadata)

        return RuleResult(
            rule_name=self.name,
            violations=all_violations,
            summary=combined_summary,
            metadata=combined_metadata,
        )

    def get_source_line(self, source: str, line_number: int) -> str:
        """Get a specific line from the source code."""
        lines = source.splitlines()
        if 1 <= line_number <= len(lines):
            return lines[line_number - 1]
        return ""

    def get_source_context(
        self,
        source: str,
        line_number: int,
        context_lines: int = 2,
    ) -> str:
        """Get source code context around a line."""
        lines = source.splitlines()
        start = max(0, line_number - context_lines - 1)
        end = min(len(lines), line_number + context_lines)
        return "\n".join(lines[start:end])
