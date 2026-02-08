"""
JSON output formatter.
"""

import json
from typing import Any

from .base import AnalysisReport, BaseFormatter


class JSONFormatter(BaseFormatter):
    """Format analysis report as JSON."""

    name = "json"
    file_extension = ".json"

    def __init__(self, indent: int = 2, sort_keys: bool = False):
        self.indent = indent
        self.sort_keys = sort_keys

    def format(self, report: AnalysisReport) -> str:
        """Format the report as JSON."""
        data = report.to_dict()
        return json.dumps(
            data,
            indent=self.indent,
            sort_keys=self.sort_keys,
            default=self._json_serializer,
        )

    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for non-serializable objects."""
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return str(obj)
