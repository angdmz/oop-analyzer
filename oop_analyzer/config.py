"""
Configuration module for OOP Analyzer.

Provides configuration options for selecting which rules to run
and customizing analyzer behavior.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RuleConfig:
    """Configuration for a specific rule."""

    enabled: bool = True
    severity: str = "warning"  # "error", "warning", "info"
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalyzerConfig:
    """
    Configuration for the OOP Analyzer.

    Attributes:
        rules: Dictionary mapping rule names to their configurations
        output_format: Output format ("json", "xml", "html")
        include_patterns: Glob patterns for files to include
        exclude_patterns: Glob patterns for files to exclude
        max_file_size: Maximum file size in bytes to analyze
    """

    rules: dict[str, RuleConfig] = field(default_factory=dict)
    output_format: str = "json"
    include_patterns: list[str] = field(default_factory=lambda: ["*.py"])
    exclude_patterns: list[str] = field(
        default_factory=lambda: ["**/test_*.py", "**/*_test.py", "**/tests/**"]
    )
    max_file_size: int = 10 * 1024 * 1024  # 10 MB

    # Available rules with their default configurations
    AVAILABLE_RULES = {
        "encapsulation": "Check for direct property access (tell don't ask)",
        "coupling": "Measure coupling and show dependency graph",
        "null_object": "Detect None usage replaceable by Null Object pattern",
        "polymorphism": "Find if blocks replaceable by polymorphism",
        "functions_to_objects": "Detect functions that could be objects",
        "type_code": "Detect type code conditionals replaceable by polymorphism",
        "reference_exposure": "Detect methods exposing internal mutable state",
        "dictionary_usage": "Detect dictionary usage that should be objects",
        "boolean_flag": "Detect boolean flag parameters causing behavior branching",
    }

    def __post_init__(self) -> None:
        # Initialize all rules with defaults if not specified
        for rule_name in self.AVAILABLE_RULES:
            if rule_name not in self.rules:
                self.rules[rule_name] = RuleConfig()

    def enable_rule(self, rule_name: str, **options: Any) -> None:
        """Enable a specific rule with optional configuration."""
        if rule_name not in self.AVAILABLE_RULES:
            raise ValueError(f"Unknown rule: {rule_name}")
        self.rules[rule_name] = RuleConfig(enabled=True, options=options)

    def disable_rule(self, rule_name: str) -> None:
        """Disable a specific rule."""
        if rule_name in self.rules:
            self.rules[rule_name].enabled = False

    def enable_only(self, *rule_names: str) -> None:
        """Enable only the specified rules, disable all others."""
        for rule_name in self.AVAILABLE_RULES:
            if rule_name in rule_names:
                self.rules[rule_name] = RuleConfig(enabled=True)
            else:
                self.rules[rule_name] = RuleConfig(enabled=False)

    def get_enabled_rules(self) -> list[str]:
        """Get list of enabled rule names."""
        return [name for name, config in self.rules.items() if config.enabled]

    def is_rule_enabled(self, rule_name: str) -> bool:
        """Check if a rule is enabled."""
        return rule_name in self.rules and self.rules[rule_name].enabled

    @classmethod
    def from_file(cls, config_path: str | Path) -> "AnalyzerConfig":
        """Load configuration from a JSON file."""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path) as f:
            data = json.load(f)

        rules = {}
        for rule_name, rule_data in data.get("rules", {}).items():
            if isinstance(rule_data, bool):
                rules[rule_name] = RuleConfig(enabled=rule_data)
            elif isinstance(rule_data, dict):
                rules[rule_name] = RuleConfig(
                    enabled=rule_data.get("enabled", True),
                    severity=rule_data.get("severity", "warning"),
                    options=rule_data.get("options", {}),
                )

        return cls(
            rules=rules,
            output_format=data.get("output_format", "json"),
            include_patterns=data.get("include_patterns", ["*.py"]),
            exclude_patterns=data.get(
                "exclude_patterns",
                ["**/test_*.py", "**/*_test.py", "**/tests/**"],
            ),
            max_file_size=data.get("max_file_size", 10 * 1024 * 1024),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "rules": {
                name: {
                    "enabled": config.enabled,
                    "severity": config.severity,
                    "options": config.options,
                }
                for name, config in self.rules.items()
            },
            "output_format": self.output_format,
            "include_patterns": self.include_patterns,
            "exclude_patterns": self.exclude_patterns,
            "max_file_size": self.max_file_size,
        }

    def save(self, config_path: str | Path) -> None:
        """Save configuration to a JSON file."""
        path = Path(config_path)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def default(cls) -> "AnalyzerConfig":
        """Create a default configuration with all rules enabled."""
        return cls()

    @classmethod
    def minimal(cls) -> "AnalyzerConfig":
        """Create a minimal configuration with only essential rules."""
        config = cls()
        config.enable_only("encapsulation", "coupling")
        return config
