"""
Tests for the configuration module.
"""

import json
from pathlib import Path

import pytest

from oop_analyzer.config import AnalyzerConfig, RuleConfig


class TestRuleConfig:
    """Tests for RuleConfig dataclass."""

    def test_default_values(self):
        """Test default RuleConfig values."""
        config = RuleConfig()

        assert config.enabled is True
        assert config.severity == "warning"
        assert config.options == {}

    def test_custom_values(self):
        """Test RuleConfig with custom values."""
        config = RuleConfig(
            enabled=False,
            severity="error",
            options={"max_params": 5},
        )

        assert config.enabled is False
        assert config.severity == "error"
        assert config.options["max_params"] == 5


class TestAnalyzerConfig:
    """Tests for AnalyzerConfig class."""

    def test_default_config(self):
        """Test default configuration has all rules enabled."""
        config = AnalyzerConfig.default()

        assert len(config.get_enabled_rules()) == len(AnalyzerConfig.AVAILABLE_RULES)
        for rule_name in AnalyzerConfig.AVAILABLE_RULES:
            assert config.is_rule_enabled(rule_name)

    def test_minimal_config(self):
        """Test minimal configuration has only essential rules."""
        config = AnalyzerConfig.minimal()

        enabled = config.get_enabled_rules()
        assert "encapsulation" in enabled
        assert "coupling" in enabled
        assert len(enabled) == 2

    def test_enable_rule(self):
        """Test enabling a specific rule."""
        config = AnalyzerConfig()
        config.disable_rule("encapsulation")
        assert not config.is_rule_enabled("encapsulation")

        config.enable_rule("encapsulation", max_chain_length=2)
        assert config.is_rule_enabled("encapsulation")
        assert config.rules["encapsulation"].options["max_chain_length"] == 2

    def test_enable_unknown_rule_raises(self):
        """Test enabling unknown rule raises ValueError."""
        config = AnalyzerConfig()

        with pytest.raises(ValueError, match="Unknown rule"):
            config.enable_rule("nonexistent_rule")

    def test_disable_rule(self):
        """Test disabling a specific rule."""
        config = AnalyzerConfig.default()
        assert config.is_rule_enabled("encapsulation")

        config.disable_rule("encapsulation")
        assert not config.is_rule_enabled("encapsulation")

    def test_enable_only(self):
        """Test enabling only specific rules."""
        config = AnalyzerConfig.default()
        config.enable_only("encapsulation", "null_object")

        enabled = config.get_enabled_rules()
        assert len(enabled) == 2
        assert "encapsulation" in enabled
        assert "null_object" in enabled
        assert "coupling" not in enabled

    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = AnalyzerConfig.default()
        data = config.to_dict()

        assert "rules" in data
        assert "output_format" in data
        assert "include_patterns" in data
        assert "exclude_patterns" in data
        assert "max_file_size" in data

    def test_save_and_load(self, temp_dir: Path):
        """Test saving and loading configuration."""
        config = AnalyzerConfig.default()
        config.disable_rule("polymorphism")
        config.output_format = "html"

        config_path = temp_dir / "config.json"
        config.save(config_path)

        loaded = AnalyzerConfig.from_file(config_path)

        assert loaded.output_format == "html"
        assert not loaded.is_rule_enabled("polymorphism")
        assert loaded.is_rule_enabled("encapsulation")

    def test_load_nonexistent_file_raises(self):
        """Test loading non-existent config file raises error."""
        with pytest.raises(FileNotFoundError):
            AnalyzerConfig.from_file("/nonexistent/config.json")

    def test_from_file_with_bool_rules(self, temp_dir: Path):
        """Test loading config with boolean rule values."""
        config_data = {
            "rules": {
                "encapsulation": True,
                "coupling": False,
            },
            "output_format": "xml",
        }

        config_path = temp_dir / "config.json"
        config_path.write_text(json.dumps(config_data))

        config = AnalyzerConfig.from_file(config_path)

        assert config.is_rule_enabled("encapsulation")
        assert not config.is_rule_enabled("coupling")
        assert config.output_format == "xml"

    def test_from_file_with_dict_rules(self, temp_dir: Path):
        """Test loading config with detailed rule configurations."""
        config_data = {
            "rules": {
                "encapsulation": {
                    "enabled": True,
                    "severity": "error",
                    "options": {"allow_self_access": False},
                },
            },
        }

        config_path = temp_dir / "config.json"
        config_path.write_text(json.dumps(config_data))

        config = AnalyzerConfig.from_file(config_path)

        assert config.is_rule_enabled("encapsulation")
        assert config.rules["encapsulation"].severity == "error"
        assert config.rules["encapsulation"].options["allow_self_access"] is False

    def test_default_exclude_patterns(self):
        """Test default exclude patterns include test files."""
        config = AnalyzerConfig.default()

        assert "**/test_*.py" in config.exclude_patterns
        assert "**/*_test.py" in config.exclude_patterns
        assert "**/tests/**" in config.exclude_patterns

    def test_default_include_patterns(self):
        """Test default include patterns include Python files."""
        config = AnalyzerConfig.default()

        assert "*.py" in config.include_patterns
