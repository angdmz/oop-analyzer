"""
HTML output formatter.
"""

from html import escape

from .base import AnalysisReport, BaseFormatter


class HTMLFormatter(BaseFormatter):
    """Format analysis report as HTML."""

    name = "html"
    file_extension = ".html"

    def format(self, report: AnalysisReport) -> str:
        """Format the report as HTML."""
        html_parts = [
            self._get_html_header(),
            self._get_summary_section(report),
            self._get_results_section(report),
            self._get_html_footer(),
        ]
        return "\n".join(html_parts)

    def _get_html_header(self) -> str:
        """Get HTML document header with styles."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OOP Analysis Report</title>
    <style>
        :root {
            --bg-color: #1a1a2e;
            --card-bg: #16213e;
            --text-color: #eee;
            --accent: #0f3460;
            --error: #e94560;
            --warning: #f39c12;
            --info: #3498db;
            --success: #27ae60;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-color);
            color: var(--text-color);
            line-height: 1.6;
            padding: 2rem;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: var(--text-color); margin-bottom: 1rem; }
        h2 { color: var(--text-color); margin: 1.5rem 0 1rem; border-bottom: 2px solid var(--accent); padding-bottom: 0.5rem; }
        h3 { color: var(--text-color); margin: 1rem 0 0.5rem; }
        .summary-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 1rem 0;
        }
        .card {
            background: var(--card-bg);
            padding: 1.5rem;
            border-radius: 8px;
            text-align: center;
        }
        .card-value { font-size: 2.5rem; font-weight: bold; }
        .card-label { color: #aaa; font-size: 0.9rem; }
        .severity-error { color: var(--error); }
        .severity-warning { color: var(--warning); }
        .severity-info { color: var(--info); }
        .rule-section {
            background: var(--card-bg);
            border-radius: 8px;
            padding: 1.5rem;
            margin: 1rem 0;
        }
        .violation {
            background: var(--accent);
            border-radius: 4px;
            padding: 1rem;
            margin: 0.5rem 0;
            border-left: 4px solid var(--warning);
        }
        .violation.error { border-left-color: var(--error); }
        .violation.info { border-left-color: var(--info); }
        .violation-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }
        .violation-location { font-family: monospace; color: #aaa; font-size: 0.85rem; }
        .violation-message { margin-bottom: 0.5rem; }
        .violation-suggestion {
            font-size: 0.9rem;
            color: var(--success);
            font-style: italic;
        }
        .code-snippet {
            background: #0d1117;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.85rem;
            overflow-x: auto;
            margin-top: 0.5rem;
        }
        .badge {
            display: inline-block;
            padding: 0.2rem 0.6rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: bold;
            text-transform: uppercase;
        }
        .badge-error { background: var(--error); }
        .badge-warning { background: var(--warning); color: #000; }
        .badge-info { background: var(--info); }
        .files-list {
            background: var(--card-bg);
            border-radius: 8px;
            padding: 1rem;
            max-height: 200px;
            overflow-y: auto;
        }
        .files-list li { font-family: monospace; font-size: 0.85rem; padding: 0.2rem 0; }
        ul { list-style: none; }
        .timestamp { color: #666; font-size: 0.85rem; margin-top: 2rem; text-align: center; }
    </style>
</head>
<body>
<div class="container">
    <h1>OOP Analysis Report</h1>
"""

    def _get_html_footer(self) -> str:
        """Get HTML document footer."""
        return """
</div>
</body>
</html>"""

    def _get_summary_section(self, report: AnalysisReport) -> str:
        """Generate summary section."""
        severity = report.violations_by_severity
        return f"""
    <div class="summary-cards">
        <div class="card">
            <div class="card-value">{len(report.files_analyzed)}</div>
            <div class="card-label">Files Analyzed</div>
        </div>
        <div class="card">
            <div class="card-value">{report.total_violations}</div>
            <div class="card-label">Total Violations</div>
        </div>
        <div class="card">
            <div class="card-value severity-error">{severity.get("error", 0)}</div>
            <div class="card-label">Errors</div>
        </div>
        <div class="card">
            <div class="card-value severity-warning">{severity.get("warning", 0)}</div>
            <div class="card-label">Warnings</div>
        </div>
        <div class="card">
            <div class="card-value severity-info">{severity.get("info", 0)}</div>
            <div class="card-label">Info</div>
        </div>
    </div>

    <h2>Files Analyzed</h2>
    <div class="files-list">
        <ul>
            {"".join(f"<li>{escape(f)}</li>" for f in report.files_analyzed)}
        </ul>
    </div>
"""

    def _get_results_section(self, report: AnalysisReport) -> str:
        """Generate results section for each rule."""
        sections = ["<h2>Analysis Results</h2>"]

        for rule_name, result in report.results.items():
            section = f"""
    <div class="rule-section">
        <h3>{escape(rule_name.replace("_", " ").title())}
            <span class="badge badge-{"error" if result.violation_count > 10 else "warning" if result.violation_count > 0 else "info"}">
                {result.violation_count} violations
            </span>
        </h3>
"""
            if result.violations:
                for v in result.violations[:50]:  # Limit to 50 per rule
                    severity_class = v.severity
                    section += f"""
        <div class="violation {severity_class}">
            <div class="violation-header">
                <span class="badge badge-{severity_class}">{escape(v.severity)}</span>
                <span class="violation-location">{escape(v.file_path)}:{v.line}:{v.column}</span>
            </div>
            <div class="violation-message">{escape(v.message)}</div>
"""
                    if v.suggestion:
                        section += f'            <div class="violation-suggestion">💡 {escape(v.suggestion)}</div>\n'
                    if v.code_snippet:
                        section += f'            <div class="code-snippet">{escape(v.code_snippet)}</div>\n'
                    section += "        </div>\n"

                if len(result.violations) > 50:
                    section += (
                        f"        <p>... and {len(result.violations) - 50} more violations</p>\n"
                    )
            else:
                section += "        <p>✅ No violations found</p>\n"

            section += "    </div>\n"
            sections.append(section)

        sections.append(f'    <p class="timestamp">Generated: {report.timestamp.isoformat()}</p>')
        return "\n".join(sections)
