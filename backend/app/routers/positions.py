"""
Position endpoints for the map view and vessel track history.

Routes::

    GET  /api/map/positions              — current positions for map
    GET  /api/vessels/{imo}/positions     — position history for a vessel
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.position import VesselPosition
from app.models.vessel import Vessel
from app.schemas.position import (
    CurrentPositionResponse,
    PositionHistoryResponse,
    PositionResponse,
)

router = APIRouter(tags=["Positions"])


@router.get(
    "/api/map/positions",
    response_model=CurrentPositionResponse,
    summary="Get current vessel positions for map",
)
async def get_current_positions(
    bbox: str | None = Query(
        None,
        description="Bounding box: min_lon,min_lat,max_lon,max_lat",
    ),
    vessel_type: str | None = Query(None, description="Filter by vessel type"),
    limit: int = Query(1000, ge=1, le=5000, description="Maximum number of current positions"),
    active_minutes: int = Query(
        720,
        ge=0,
        le=43200,
        description="Only include latest positions newer than this many minutes; 0 disables the age filter",
    ),
    db: AsyncSession = Depends(get_db),
) -> CurrentPositionResponse:
    """Return the latest position for every vessel, optionally within a bounding box.

    The bounding box should be a comma-separated string of four floats:
    ``min_lon,min_lat,max_lon,max_lat``.
    """
    cutoff = (
        datetime.now(timezone.utc) - timedelta(minutes=active_minutes)
        if active_minutes > 0
        else None
    )
    latest_times_query = select(
        VesselPosition.mmsi,
        func.max(VesselPosition.time).label("latest_time"),
    ).group_by(VesselPosition.mmsi)
    if cutoff is not None:
        latest_times_query = latest_times_query.where(VesselPosition.time >= cutoff)

    latest_times = latest_times_query.subquery()
    current_positions_query = (
        select(VesselPosition)
        .join(
            latest_times,
            and_(
                VesselPosition.mmsi == latest_times.c.mmsi,
                VesselPosition.time == latest_times.c.latest_time,
            ),
        )
        .order_by(VesselPosition.time.desc())
    )

    # Apply bounding box filter
    bbox_values: list[float] | None = None
    if bbox is not None:
        try:
            parts = [float(p.strip()) for p in bbox.split(",")]
            if len(parts) != 4:
                raise ValueError
            min_lon, min_lat, max_lon, max_lat = parts
            if not (-90.0 <= min_lat <= 90.0 and -90.0 <= max_lat <= 90.0):
                raise ValueError("Latitude must be between -90 and 90")
            if min_lat > max_lat:
                raise ValueError("min_lat cannot be greater than max_lat")
            if not (-180.0 <= min_lon <= 180.0 and -180.0 <= max_lon <= 180.0):
                raise ValueError("Longitude must be between -180 and 180")
            bbox_values = parts
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid bbox parameters: {exc}" if str(exc) else "bbox must be 4 comma-separated floats: min_lon,min_lat,max_lon,max_lat",
            )
        if min_lon <= max_lon:
            lon_filter = VesselPosition.longitude.between(min_lon, max_lon)
        else:
            lon_filter = or_(
                VesselPosition.longitude >= min_lon,
                VesselPosition.longitude <= max_lon,
            )
        current_positions_query = current_positions_query.where(
            VesselPosition.latitude.between(min_lat, max_lat),
            lon_filter,
        )

    # If filtering by vessel type, join with vessels table
    if vessel_type is not None:
        current_positions_query = current_positions_query.join(
            Vessel, Vessel.mmsi == VesselPosition.mmsi
        ).where(Vessel.vessel_type.ilike(f"%{vessel_type}%"))

    result = await db.execute(current_positions_query.limit(limit))
    rows = result.scalars().all()

    positions = [
        PositionResponse.model_validate(pos)
        for pos in rows
    ]

    return CurrentPositionResponse(
        positions=positions,
        total=len(positions),
        bbox=bbox_values,
    )


@router.get(
    "/api/vessels/{imo}/positions",
    response_model=PositionHistoryResponse,
    summary="Get position history for a vessel",
)
async def get_position_history(
    imo: int,
    start_time: datetime | None = Query(None, description="Start of time range (ISO 8601)"),
    end_time: datetime | None = Query(None, description="End of time range (ISO 8601)"),
    limit: int = Query(1000, ge=1, le=10000, description="Maximum number of positions"),
    db: AsyncSession = Depends(get_db),
) -> PositionHistoryResponse:
    """Retrieve historical position track for a vessel identified by IMO.

    Raises:
        HTTPException 404: If the vessel does not exist.
    """
    # Verify vessel exists and get MMSI
    vessel_result = await db.execute(select(Vessel).where(Vessel.imo == imo))
    vessel = vessel_result.scalar_one_or_none()

    if vessel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vessel with IMO {imo} not found",
        )

    if vessel.mmsi is None:
        return PositionHistoryResponse(
            imo=imo,
            mmsi=None,
            positions=[],
            total=0,
        )

    # Query positions by MMSI
    query = (
        select(VesselPosition)
        .where(VesselPosition.mmsi == vessel.mmsi)
        .order_by(VesselPosition.time.desc())
    )

    if start_time is not None:
        query = query.where(VesselPosition.time >= start_time)
    if end_time is not None:
        query = query.where(VesselPosition.time <= end_time)

    query = query.limit(limit)

    result = await db.execute(query)
    positions = result.scalars().all()

    return PositionHistoryResponse(
        imo=imo,
        mmsi=vessel.mmsi,
        positions=[PositionResponse.model_validate(p) for p in positions],
        total=len(positions),
    )
