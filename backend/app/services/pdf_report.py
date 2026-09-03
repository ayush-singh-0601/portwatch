"""
WeasyPrint PDF report generator service.

Renders Jinja2 HTML templates and converts them to PDF using WeasyPrint.
Falls back to HTML output if WeasyPrint is not available (e.g. missing
Cairo/Pango system libraries).
"""

import logging
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

# Template directory
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

# Jinja2 environment
_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=True,
    trim_blocks=True,
    lstrip_blocks=True,
)


def _risk_class(score: float | int | None) -> str:
    if score is None:
        return "risk-unknown"
    if score <= 30:
        return "risk-low"
    if score <= 60:
        return "risk-med"
    return "risk-high"


def _format_num(val: float | int | None) -> str:
    if val is None:
        return "—"
    return f"{val:,.0f}" if isinstance(val, (int, float)) else str(val)


_jinja_env.filters["risk_class"] = _risk_class
_jinja_env.filters["format_num"] = _format_num




def render_html(template_name: str, context: dict[str, Any]) -> str:
    """Render a Jinja2 template to an HTML string.

    Args:
        template_name: Name of the template file (e.g. 'intel_report.html').
        context: Template variables.

    Returns:
        Rendered HTML string.
    """
    template = _jinja_env.get_template(template_name)
    return template.render(**context)


def html_to_pdf(html_content: str, output_path: str | Path) -> Path:
    """Convert an HTML string to PDF using WeasyPrint.

    Args:
        html_content: Rendered HTML string.
        output_path: Path to write the PDF file.

    Returns:
        Path to the generated PDF file.

    Raises:
        RuntimeError: If WeasyPrint is not available.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from weasyprint import HTML as WeasyHTML

        WeasyHTML(string=html_content).write_pdf(
            str(output_path),
            optimize_images=True,
        )
        logger.info(f"PDF generated: {output_path} ({output_path.stat().st_size} bytes)")
        return output_path

    except ImportError:
        logger.warning(
            "WeasyPrint not installed. Falling back to HTML output. "
            "Install with: pip install weasyprint"
        )
        html_path = output_path.with_suffix(".html")
        html_path.write_text(html_content, encoding="utf-8")
        logger.info(f"HTML fallback generated: {html_path}")
        return html_path

    except OSError as e:
        logger.warning(
            f"WeasyPrint failed (missing system libraries?): {e}. "
            "Falling back to HTML output."
        )
        html_path = output_path.with_suffix(".html")
        html_path.write_text(html_content, encoding="utf-8")
        return html_path


def generate_report_pdf(
    template_name: str,
    context: dict[str, Any],
    output_path: str | Path,
) -> Path:
    """Render template and convert to PDF in one step.

    Args:
        template_name: Jinja2 template filename.
        context: Template variables.
        output_path: Output PDF path.

    Returns:
        Path to the generated file (PDF or HTML fallback).
    """
    html = render_html(template_name, context)
    return html_to_pdf(html, output_path)
