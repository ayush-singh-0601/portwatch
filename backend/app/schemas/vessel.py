"""
Pydantic schemas for vessel request / response payloads.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class VesselBase(BaseModel):
    """Shared fields for vessel creation and response."""

    name: str = Field(..., max_length=255, description="Vessel name")
    mmsi: int | None = Field(None, description="Maritime Mobile Service Identity (9-digit)")
    flag: str | None = Field(None, max_length=3, description="Flag state ISO 3166-1 alpha-3")
    vessel_type: str | None = Field(None, max_length=100, description="Vessel type category")
    gross_tonnage: int | None = Field(None, ge=0, description="Gross tonnage")
    dwt: int | None = Field(None, ge=0, description="Deadweight tonnage")
    year_built: int | None = Field(None, ge=1800, le=2100, description="Year of build")
    call_sign: str | None = Field(None, max_length=20, description="Radio call sign")


class VesselCreate(VesselBase):
    """Payload for creating a new vessel record."""

    imo: int = Field(..., ge=1000000, le=9999999, description="IMO number (7-digit)")


class VesselResponse(VesselBase):
    """Full vessel response with metadata."""

    imo: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VesselListResponse(BaseModel):
    """Paginated list of vessels."""

    items: list[VesselResponse]
    total: int = Field(..., ge=0, description="Total matching records")
    page: int = Field(..., ge=1)
    per_page: int = Field(..., ge=1)
    pages: int = Field(..., ge=0, description="Total number of pages")


class VesselSearchParams(BaseModel):
    """Query parameters for vessel search."""

    name: str | None = Field(None, description="Partial name match (case-insensitive)")
    imo: int | None = Field(None, description="Exact IMO number match")
    mmsi: int | None = Field(None, description="Exact MMSI match")
    vessel_type: str | None = Field(None, description="Vessel type filter")
    flag: str | None = Field(None, description="Flag state filter (ISO alpha-3)")
    page: int = Field(1, ge=1, description="Page number")
    per_page: int = Field(20, ge=1, le=100, description="Results per page")
