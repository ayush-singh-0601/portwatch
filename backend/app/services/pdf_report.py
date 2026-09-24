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

logger = logging.getLogger(__name__)

# Template directory
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

# Jinja2 environment
_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=True,
    trim_blocks=True,
    lstrip_blocks=True,
)


class ReportPath(Path):
    """Path subclass tracking format, content_type, and extension metadata."""
    format: str = "pdf"
    content_type: str = "application/pdf"
    extension: str = ".pdf"


def get_report_metadata(filepath: str | Path, is_fallback: bool = False) -> dict[str, str]:
    """Return report metadata including format, extension, and content_type."""
    path = Path(filepath)
    if is_fallback or path.suffix.lower() == ".html":
        return {
            "format": "html",
            "extension": ".html",
            "content_type": "text/html",
        }
    return {
        "format": "pdf",
        "extension": ".pdf",
        "content_type": "application/pdf",
    }


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


def html_to_pdf(
    html_content: str,
    output_path: str | Path,
    report_metadata: dict[str, Any] | None = None,
) -> Path:
    """Convert an HTML string to PDF using WeasyPrint.

    Args:
        html_content: Rendered HTML string.
        output_path: Path to write the PDF file.
        report_metadata: Optional dict to receive report format and content type.

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
        if report_metadata is not None:
            report_metadata["format"] = "pdf"
            report_metadata["extension"] = ".pdf"
            report_metadata["content_type"] = "application/pdf"
        result_path = ReportPath(output_path)
        result_path.format = "pdf"
        result_path.extension = ".pdf"
        result_path.content_type = "application/pdf"
        return result_path

    except ImportError:
        logger.warning(
            "WeasyPrint not installed. Falling back to HTML output. "
            "Install with: pip install weasyprint"
        )
        html_path = output_path.with_suffix(".html")
        html_path.write_text(html_content, encoding="utf-8")
        logger.info(f"HTML fallback generated: {html_path}")
        if report_metadata is not None:
            report_metadata["format"] = "html"
            report_metadata["extension"] = ".html"
            report_metadata["content_type"] = "text/html"
        result_path = ReportPath(html_path)
        result_path.format = "html"
        result_path.extension = ".html"
        result_path.content_type = "text/html"
        return result_path

    except OSError as e:
        logger.warning(
            f"WeasyPrint failed (missing system libraries?): {e}. "
            "Falling back to HTML output."
        )
        html_path = output_path.with_suffix(".html")
        html_path.write_text(html_content, encoding="utf-8")
        if report_metadata is not None:
            report_metadata["format"] = "html"
            report_metadata["extension"] = ".html"
            report_metadata["content_type"] = "text/html"
        result_path = ReportPath(html_path)
        result_path.format = "html"
        result_path.extension = ".html"
        result_path.content_type = "text/html"
        return result_path


def generate_report_pdf(
    template_name: str,
    context: dict[str, Any],
    output_path: str | Path,
    report_metadata: dict[str, Any] | None = None,
) -> Path:
    """Render template and convert to PDF in one step.

    Args:
        template_name: Jinja2 template filename.
        context: Template variables.
        output_path: Output PDF path.
        report_metadata: Optional dict populated with report format and content type.

    Returns:
        Path to the generated file (PDF or HTML fallback).
    """
    if report_metadata is None and isinstance(context, dict):
        if "report_metadata" in context and isinstance(context["report_metadata"], dict):
            report_metadata = context["report_metadata"]
        elif "metadata" in context and isinstance(context["metadata"], dict):
            report_metadata = context["metadata"]
    html = render_html(template_name, context)
    return html_to_pdf(html, output_path, report_metadata=report_metadata)
