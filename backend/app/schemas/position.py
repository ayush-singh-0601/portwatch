"""
Pydantic schemas for vessel position data.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class PositionBase(BaseModel):
    """Core position fields shared across responses."""

    mmsi: int
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    speed: float | None = Field(None, ge=0, description="Speed over ground (knots)")
    course: float | None = Field(None, ge=0, le=360, description="Course over ground (degrees)")
    heading: float | None = Field(None, ge=0, le=360, description="True heading (degrees)")
    nav_status: int | None = Field(None, ge=0, le=15, description="AIS navigational status code")
    msg_type: int | None = Field(None, description="AIS message type")


class PositionResponse(PositionBase):
    """Single position report with timestamp."""

    time: datetime

    model_config = {"from_attributes": True}


class PositionHistoryResponse(BaseModel):
    """Historical position track for a vessel."""

    imo: int
    mmsi: int | None = None
    positions: list[PositionResponse]
    total: int = Field(..., ge=0, description="Total positions in the time range")


class CurrentPositionResponse(BaseModel):
    """Current positions for the map view (multiple vessels)."""

    positions: list[PositionResponse]
    total: int = Field(..., ge=0, description="Number of vessels with current positions")
    bbox: list[float] | None = Field(
        None,
        description="Bounding box filter applied [min_lon, min_lat, max_lon, max_lat]",
    )
