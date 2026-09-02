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

from app.agents.intel_report import IntelReportAgent
from app.database import get_db
from app.models.vessel import Vessel
from app.schemas.report import ReportRequest, ReportResponse, ReportStatusResponse

router = APIRouter(tags=["Reports"])

# In-memory store for generated reports (production would use S3 / object storage)
_MAX_STORE_SIZE = 500
_report_store: dict[str, dict] = {}


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

    Uses IntelReportAgent to gather all intelligence (identity, ownership,
    sanctions, risk score, dark events, port calls) and render a PDF via
    Jinja2 + WeasyPrint.

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

    # Use IntelReportAgent for full report generation
    agent = IntelReportAgent(db)
    result = await agent.generate_report(
        vessel_imo=imo,
        sections=request.sections,
        output_format=request.format.value,
    )

    # Prevent unbounded memory growth in report store
    if len(_report_store) >= _MAX_STORE_SIZE:
        oldest_key = next(iter(_report_store))
        _report_store.pop(oldest_key, None)

    # Store report metadata for download
    _report_store[result["report_id"]] = {
        **result,
        "status": "completed",
    }

    return ReportResponse(
        report_id=result["report_id"],
        vessel_imo=imo,
        generated_at=datetime.now(timezone.utc),
        format=request.format,
        download_url=result["download_url"],
        file_size_bytes=result["file_size_bytes"],
    )


_REPORT_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")


@router.get(
    "/api/reports/{report_id}",
    summary="Download a generated report",
    response_description="The report file (PDF or HTML)",
)
async def download_report(
    report_id: str,
) -> FileResponse:
    """Download a previously generated intelligence report by ID.

    Args:
        report_id: Unique report identifier returned by the generate endpoint.

    Returns:
        The report file as a downloadable attachment.

    Raises:
        HTTPException 400: If the report ID contains invalid path characters.
        HTTPException 404: If the report does not exist.
    """
    if not report_id or not _REPORT_ID_REGEX.match(report_id) or ".." in report_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid report ID format",
        )

    report_meta = _report_store.get(report_id)

    if report_meta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {report_id} not found",
        )

    filepath = Path(report_meta["filepath"]).resolve()
    if not filepath.exists() or not filepath.is_file():
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
        headers={"Content-Disposition": f'attachment; filename="{filepath.name}"'},
    )
