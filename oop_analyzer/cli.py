"""
Command-line interface for OOP Analyzer.
"""

import argparse
import sys
from pathlib import Path

from .analyzer import OOPAnalyzer
from .config import AnalyzerConfig


def main() -> int:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="oop-analyzer",
        description="Analyze Python code for OOP best practices",
    )

    parser.add_argument(
        "path",
        type=str,
        nargs="?",
        help="Path to Python file, module, or directory to analyze",
    )

    parser.add_argument(
        "-f",
        "--format",
        choices=["json", "xml", "html"],
        default="json",
        help="Output format (default: json)",
    )

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output file path (default: stdout)",
    )

    parser.add_argument(
        "-c",
        "--config",
        type=str,
        help="Path to configuration file",
    )

    parser.add_argument(
        "--rules",
        type=str,
        nargs="+",
        help="Enable only specific rules",
    )

    parser.add_argument(
        "--disable-rules",
        type=str,
        nargs="+",
        help="Disable specific rules",
    )

    parser.add_argument(
        "--list-rules",
        action="store_true",
        help="List available rules and exit",
    )

    parser.add_argument(
        "--init-config",
        type=str,
        metavar="FILE",
        help="Generate a default configuration file",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    # Handle --list-rules
    if args.list_rules:
        print("Available rules:")
        for name, desc in AnalyzerConfig.AVAILABLE_RULES.items():
            print(f"  {name}: {desc}")
        return 0

    # Handle --init-config
    if args.init_config:
        config = AnalyzerConfig.default()
        config.save(args.init_config)
        print(f"Configuration saved to: {args.init_config}")
        return 0

    # Load or create configuration
    if args.config:
        try:
            config = AnalyzerConfig.from_file(args.config)
        except FileNotFoundError:
            print(f"Error: Config file not found: {args.config}", file=sys.stderr)
            return 1
    else:
        config = AnalyzerConfig.default()

    # Apply command-line rule overrides
    if args.rules:
        config.enable_only(*args.rules)

    if args.disable_rules:
        for rule in args.disable_rules:
            config.disable_rule(rule)

    # Set output format
    config.output_format = args.format

    # Validate path (required for analysis)
    if not args.path:
        print("Error: path is required for analysis", file=sys.stderr)
        parser.print_help()
        return 1

    path = Path(args.path)
    if not path.exists():
        print(f"Error: Path does not exist: {args.path}", file=sys.stderr)
        return 1

    # Run analysis
    if args.verbose:
        print(f"Analyzing: {path}", file=sys.stderr)
        print(f"Enabled rules: {config.get_enabled_rules()}", file=sys.stderr)

    analyzer = OOPAnalyzer(config)
    report = analyzer.analyze(path)

    # Format output
    output = analyzer.format_report(report)

    # Write output
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(output, encoding="utf-8")
        if args.verbose:
            print(f"Report saved to: {output_path}", file=sys.stderr)
    else:
        print(output)

    # Return non-zero if there are errors or violations
    if report.errors:
        return 2
    if report.total_violations > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
