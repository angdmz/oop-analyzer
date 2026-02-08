"""
XML output formatter.
"""

from typing import Any
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring

from .base import AnalysisReport, BaseFormatter


class XMLFormatter(BaseFormatter):
    """Format analysis report as XML."""

    name = "xml"
    file_extension = ".xml"

    def __init__(self, pretty: bool = True):
        self.pretty = pretty

    def format(self, report: AnalysisReport) -> str:
        """Format the report as XML."""
        root = Element("oop-analysis-report")

        # Add metadata
        metadata = SubElement(root, "metadata")
        SubElement(metadata, "timestamp").text = report.timestamp.isoformat()
        SubElement(metadata, "total-files").text = str(len(report.files_analyzed))
        SubElement(metadata, "total-violations").text = str(report.total_violations)

        # Add severity summary
        severity_summary = SubElement(metadata, "violations-by-severity")
        for severity, count in report.violations_by_severity.items():
            SubElement(severity_summary, severity).text = str(count)

        # Add files analyzed
        files_elem = SubElement(root, "files-analyzed")
        for file_path in report.files_analyzed:
            SubElement(files_elem, "file").text = file_path

        # Add results for each rule
        results_elem = SubElement(root, "results")
        for rule_name, result in report.results.items():
            rule_elem = SubElement(results_elem, "rule")
            rule_elem.set("name", rule_name)

            SubElement(rule_elem, "violation-count").text = str(result.violation_count)

            # Add summary
            summary_elem = SubElement(rule_elem, "summary")
            self._dict_to_xml(summary_elem, result.summary)

            # Add violations
            violations_elem = SubElement(rule_elem, "violations")
            for violation in result.violations:
                v_elem = SubElement(violations_elem, "violation")
                SubElement(v_elem, "message").text = violation.message
                SubElement(v_elem, "file").text = violation.file_path
                SubElement(v_elem, "line").text = str(violation.line)
                SubElement(v_elem, "column").text = str(violation.column)
                SubElement(v_elem, "severity").text = violation.severity
                if violation.suggestion:
                    SubElement(v_elem, "suggestion").text = violation.suggestion
                if violation.code_snippet:
                    SubElement(v_elem, "code-snippet").text = violation.code_snippet

            # Add metadata
            if result.metadata:
                meta_elem = SubElement(rule_elem, "metadata")
                self._dict_to_xml(meta_elem, result.metadata)

        # Add errors if any
        if report.errors:
            errors_elem = SubElement(root, "errors")
            for error in report.errors:
                error_elem = SubElement(errors_elem, "error")
                self._dict_to_xml(error_elem, error)

        # Convert to string
        xml_str = tostring(root, encoding="unicode")

        if self.pretty:
            return minidom.parseString(xml_str).toprettyxml(indent="  ")
        return xml_str

    def _dict_to_xml(self, parent: Element, data: dict[str, Any]) -> None:
        """Convert a dictionary to XML elements."""
        for key, value in data.items():
            # Sanitize key for XML element name
            safe_key = self._sanitize_xml_name(key)

            if isinstance(value, dict):
                child = SubElement(parent, safe_key)
                self._dict_to_xml(child, value)
            elif isinstance(value, list):
                list_elem = SubElement(parent, safe_key)
                for item in value:
                    if isinstance(item, dict):
                        item_elem = SubElement(list_elem, "item")
                        self._dict_to_xml(item_elem, item)
                    else:
                        SubElement(list_elem, "item").text = str(item)
            else:
                SubElement(parent, safe_key).text = str(value) if value is not None else ""

    def _sanitize_xml_name(self, name: str) -> str:
        """Sanitize a string to be a valid XML element name."""
        # Replace invalid characters
        safe = name.replace(" ", "-").replace("_", "-")
        # Ensure starts with letter
        if safe and not safe[0].isalpha():
            safe = "x-" + safe
        return safe or "element"
