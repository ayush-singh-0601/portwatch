"""
Pydantic schemas for intelligence report generation and retrieval.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ReportFormat(StrEnum):
    """Supported report output formats."""

    PDF = "pdf"
    HTML = "html"


class ReportRequest(BaseModel):
    """Payload for requesting a new intelligence report."""

    sections: list[str] = Field(
        default_factory=lambda: [
            "vessel_profile",
            "ownership_structure",
            "risk_assessment",
            "sanctions_screening",
            "dark_activity",
            "port_history",
        ],
        description="Report sections to include",
    )
    format: ReportFormat = Field(
        ReportFormat.PDF,
        description="Output format for the report",
    )
    include_map: bool = Field(True, description="Include static map image in the report")


class ReportResponse(BaseModel):
    """Response after successfully generating a report."""

    report_id: str = Field(..., description="Unique identifier for the generated report")
    vessel_imo: int
    generated_at: datetime
    format: ReportFormat
    download_url: str = Field(..., description="URL to download the report")
    file_size_bytes: int | None = None


class ReportStatusResponse(BaseModel):
    """Status of an asynchronous report generation job."""

    report_id: str
    status: str = Field(..., description="pending | processing | completed | failed")
    progress: float = Field(0.0, ge=0.0, le=100.0, description="Completion percentage")
    error_message: str | None = None
    download_url: str | None = None
