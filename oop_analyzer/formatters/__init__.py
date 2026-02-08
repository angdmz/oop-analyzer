"""
Formatters module for OOP Analyzer.

Provides output formatting in JSON, XML, and HTML formats.
"""

from .base import AnalysisReport, BaseFormatter
from .html_formatter import HTMLFormatter
from .json_formatter import JSONFormatter
from .xml_formatter import XMLFormatter

__all__ = [
    "BaseFormatter",
    "AnalysisReport",
    "JSONFormatter",
    "XMLFormatter",
    "HTMLFormatter",
]

FORMATTER_REGISTRY: dict[str, type["BaseFormatter"]] = {
    "json": JSONFormatter,
    "xml": XMLFormatter,
    "html": HTMLFormatter,
}


def get_formatter(format_name: str) -> type["BaseFormatter"]:
    """Get a formatter class by name."""
    if format_name not in FORMATTER_REGISTRY:
        raise ValueError(f"Unknown format: {format_name}")
    return FORMATTER_REGISTRY[format_name]
