"""
Report generation endpoints.

Routes::

    POST  /api/vessels/{imo}/report   — generate an intel report
    GET   /api/reports/{report_id}    — download a generated report
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.vessel import Vessel
from app.schemas.report import ReportRequest, ReportResponse, ReportStatusResponse

router = APIRouter(tags=["Reports"])

# In-memory store for generated reports (production would use S3 / object storage)
_report_store: dict[str, dict] = {}

# Directory where generated reports are saved
REPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


@router.post(
    "/api/vessels/{imo}/report",
    response_model=ReportResponse,
    summary="Generate an intelligence report",
)
async def generate_report(
    imo: int,
    request: ReportRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> ReportResponse:
    """Generate a comprehensive intelligence report for a vessel.

    The report is rendered via Jinja2 templates and converted to PDF
    using WeasyPrint.

    Raises:
        HTTPException 404: If the vessel does not exist.
    """
    if request is None:
        request = ReportRequest()

    # Verify vessel
    vessel_result = await db.execute(select(Vessel).where(Vessel.imo == imo))
    vessel = vessel_result.scalar_one_or_none()

    if vessel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vessel with IMO {imo} not found",
        )

    report_id = str(uuid.uuid4())
    generated_at = datetime.now(timezone.utc)
    filename = f"portwatch_report_{imo}_{report_id[:8]}.{request.format.value}"
    filepath = REPORTS_DIR / filename

    # Generate a basic HTML report (production: full Jinja2 template)
    html_content = _build_html_report(vessel, request.sections)

    if request.format.value == "pdf":
        try:
            from weasyprint import HTML as WeasyHTML

            WeasyHTML(string=html_content).write_pdf(str(filepath))
        except Exception:
            # Fallback: save as HTML if WeasyPrint is not available
            filepath = filepath.with_suffix(".html")
            filepath.write_text(html_content, encoding="utf-8")
    else:
        filepath.write_text(html_content, encoding="utf-8")

    file_size = filepath.stat().st_size
    download_url = f"/api/reports/{report_id}"

    # Store report metadata
    _report_store[report_id] = {
        "report_id": report_id,
        "vessel_imo": imo,
        "generated_at": generated_at,
        "format": request.format,
        "filepath": str(filepath),
        "download_url": download_url,
        "file_size_bytes": file_size,
        "status": "completed",
    }

    return ReportResponse(
        report_id=report_id,
        vessel_imo=imo,
        generated_at=generated_at,
        format=request.format,
        download_url=download_url,
        file_size_bytes=file_size,
    )


@router.get(
    "/api/reports/{report_id}",
    summary="Download a generated report",
)
async def download_report(report_id: str) -> FileResponse:
    """Download a previously generated report by its ID.

    Raises:
        HTTPException 404: If the report does not exist.
    """
    report_meta = _report_store.get(report_id)

    if report_meta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found",
        )

    filepath = Path(report_meta["filepath"])
    if not filepath.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file no longer exists on disk",
        )

    media_type = (
        "application/pdf"
        if filepath.suffix == ".pdf"
        else "text/html"
    )

    return FileResponse(
        path=str(filepath),
        media_type=media_type,
        filename=filepath.name,
    )


def _build_html_report(vessel: Vessel, sections: list[str]) -> str:
    """Build a basic HTML intelligence report for a vessel.

    Args:
        vessel: The vessel ORM instance.
        sections: List of section identifiers to include.

    Returns:
        Rendered HTML string.
    """
    section_html_parts: list[str] = []

    if "vessel_profile" in sections:
        section_html_parts.append(f"""
        <section>
            <h2>Vessel Profile</h2>
            <table>
                <tr><td><strong>Name</strong></td><td>{vessel.name}</td></tr>
                <tr><td><strong>IMO</strong></td><td>{vessel.imo}</td></tr>
                <tr><td><strong>MMSI</strong></td><td>{vessel.mmsi or 'N/A'}</td></tr>
                <tr><td><strong>Flag</strong></td><td>{vessel.flag or 'N/A'}</td></tr>
                <tr><td><strong>Type</strong></td><td>{vessel.vessel_type or 'N/A'}</td></tr>
                <tr><td><strong>Gross Tonnage</strong></td><td>{vessel.gross_tonnage or 'N/A'}</td></tr>
                <tr><td><strong>DWT</strong></td><td>{vessel.dwt or 'N/A'}</td></tr>
                <tr><td><strong>Year Built</strong></td><td>{vessel.year_built or 'N/A'}</td></tr>
                <tr><td><strong>Call Sign</strong></td><td>{vessel.call_sign or 'N/A'}</td></tr>
            </table>
        </section>
        """)

    for section in sections:
        if section != "vessel_profile":
            section_html_parts.append(f"""
            <section>
                <h2>{section.replace('_', ' ').title()}</h2>
                <p><em>Data for this section will be populated by the full report engine.</em></p>
            </section>
            """)

    sections_html = "\n".join(section_html_parts)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>PortWatch Intelligence Report — {vessel.name} (IMO {vessel.imo})</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, sans-serif; margin: 40px; color: #1a1a2e; }}
        h1 {{ color: #16213e; border-bottom: 3px solid #0f3460; padding-bottom: 10px; }}
        h2 {{ color: #0f3460; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
        td {{ padding: 8px 12px; border-bottom: 1px solid #e0e0e0; }}
        td:first-child {{ width: 200px; color: #555; }}
        .header {{ background: #16213e; color: white; padding: 20px; margin: -40px -40px 30px; }}
        .header h1 {{ color: white; border-bottom-color: #e94560; }}
        .classification {{ color: #e94560; font-weight: bold; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="header">
        <p class="classification">CONFIDENTIAL — OSINT INTELLIGENCE PRODUCT</p>
        <h1>PortWatch Intelligence Report</h1>
        <p>{vessel.name} — IMO {vessel.imo}</p>
        <p>Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</p>
    </div>
    {sections_html}
    <footer>
        <hr>
        <p style="font-size: 12px; color: #888;">
            Generated by PortWatch Maritime OSINT Platform.
            This report is for authorised personnel only.
        </p>
    </footer>
</body>
</html>"""
