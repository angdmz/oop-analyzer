"""
Base classes for output formatters.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..rules.base import RuleResult


@dataclass
class AnalysisReport:
    """
    Complete analysis report containing results from all rules.

    Attributes:
        files_analyzed: List of files that were analyzed
        results: Dictionary mapping rule names to their results
        timestamp: When the analysis was performed
        config: Configuration used for the analysis
        errors: Any errors encountered during analysis
    """

    files_analyzed: list[str]
    results: dict[str, RuleResult]
    timestamp: datetime = field(default_factory=datetime.now)
    config: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)

    @property
    def total_violations(self) -> int:
        """Get total number of violations across all rules."""
        return sum(r.violation_count for r in self.results.values())

    @property
    def violations_by_severity(self) -> dict[str, int]:
        """Get violation counts grouped by severity."""
        counts: dict[str, int] = {"error": 0, "warning": 0, "info": 0}
        for result in self.results.values():
            for violation in result.violations:
                severity = violation.severity
                counts[severity] = counts.get(severity, 0) + 1
        return counts

    @property
    def rules_with_violations(self) -> list[str]:
        """Get list of rules that found violations."""
        return [name for name, result in self.results.items() if result.has_violations]

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "files_analyzed": self.files_analyzed,
            "total_files": len(self.files_analyzed),
            "total_violations": self.total_violations,
            "violations_by_severity": self.violations_by_severity,
            "timestamp": self.timestamp.isoformat(),
            "config": self.config,
            "results": {name: result.to_dict() for name, result in self.results.items()},
            "errors": self.errors,
        }


class BaseFormatter(ABC):
    """
    Abstract base class for output formatters.

    To create a new formatter:
    1. Inherit from BaseFormatter
    2. Implement the format method
    """

    name: str = "base"
    file_extension: str = ".txt"

    @abstractmethod
    def format(self, report: AnalysisReport) -> str:
        """
        Format the analysis report.

        Args:
            report: The analysis report to format

        Returns:
            Formatted string representation
        """
        pass

    def save(self, report: AnalysisReport, file_path: str) -> None:
        """
        Save the formatted report to a file.

        Args:
            report: The analysis report to save
            file_path: Path to save the report to
        """
        formatted = self.format(report)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(formatted)
