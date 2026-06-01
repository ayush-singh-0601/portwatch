"""
Position endpoints for the map view and vessel track history.

Routes::

    GET  /api/map/positions              — current positions for map
    GET  /api/vessels/{imo}/positions     — position history for a vessel
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
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
    db: AsyncSession = Depends(get_db),
) -> CurrentPositionResponse:
    """Return the latest position for every vessel, optionally within a bounding box.

    The bounding box should be a comma-separated string of four floats:
    ``min_lon,min_lat,max_lon,max_lat``.
    """
    # Build a subquery for the latest position per MMSI
    latest_sub = (
        select(
            VesselPosition.mmsi,
            VesselPosition.latitude,
            VesselPosition.longitude,
            VesselPosition.speed,
            VesselPosition.course,
            VesselPosition.heading,
            VesselPosition.nav_status,
            VesselPosition.msg_type,
            VesselPosition.time,
        )
        .distinct(VesselPosition.mmsi)
        .order_by(VesselPosition.mmsi, VesselPosition.time.desc())
    )

    # Apply bounding box filter
    bbox_values: list[float] | None = None
    if bbox is not None:
        try:
            parts = [float(p.strip()) for p in bbox.split(",")]
            if len(parts) != 4:
                raise ValueError
            min_lon, min_lat, max_lon, max_lat = parts
            bbox_values = parts
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="bbox must be 4 comma-separated floats: min_lon,min_lat,max_lon,max_lat",
            )
        latest_sub = latest_sub.where(
            VesselPosition.latitude.between(min_lat, max_lat),
            VesselPosition.longitude.between(min_lon, max_lon),
        )

    # If filtering by vessel type, join with vessels table
    if vessel_type is not None:
        latest_sub = latest_sub.join(
            Vessel, Vessel.mmsi == VesselPosition.mmsi
        ).where(Vessel.vessel_type.ilike(f"%{vessel_type}%"))

    result = await db.execute(latest_sub)
    rows = result.all()

    positions = [
        PositionResponse(
            mmsi=row.mmsi,
            latitude=row.latitude,
            longitude=row.longitude,
            speed=row.speed,
            course=row.course,
            heading=row.heading,
            nav_status=row.nav_status,
            msg_type=row.msg_type,
            time=row.time,
        )
        for row in rows
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
