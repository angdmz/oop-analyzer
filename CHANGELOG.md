# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-02-08

### Added
- Initial release of OOP Analyzer
- **Encapsulation Rule**: Detects direct property access violations (Tell Don't Ask principle)
  - Skips module attribute access (e.g., `json.JSONEncoder`)
  - Skips class inheritance bases
- **Coupling Rule**: Measures coupling and builds dependency graphs
  - Differentiates stdlib (info) vs external dependencies (warning)
  - Shows import locations in reports
- **Null Object Rule**: Finds None usage replaceable by Null Object pattern
  - Detects Optional type hints in parameters
- **Polymorphism Rule**: Detects if/elif chains replaceable by polymorphism
- **Functions to Objects Rule**: Identifies functions that could be objects
- **Type Code Rule**: Detects type code conditionals (State/Strategy pattern candidates)
- **Reference Exposure Rule**: Finds methods exposing internal mutable state
- **Dictionary Usage Rule**: Detects dictionaries that should be dataclasses/Pydantic models
- **Boolean Flag Rule**: Detects boolean flag parameters causing behavior branching
- CLI with JSON, XML, and HTML output formats
- Configuration via `.oop-analyzer.toml` or `pyproject.toml`
- Comprehensive test suite (200+ tests)
- Example files for each rule

[Unreleased]: https://github.com/agustindorda/oop-analyzer/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/agustindorda/oop-analyzer/releases/tag/v0.1.0
