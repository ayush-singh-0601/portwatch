"""
Vessel CRUD and search endpoints.

Routes::

    GET  /api/vessels           — list / search vessels
    GET  /api/vessels/{imo}     — get single vessel by IMO
"""

import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.vessel import Vessel
from app.schemas.vessel import VesselListResponse, VesselResponse

router = APIRouter(prefix="/api/vessels", tags=["Vessels"])


@router.get(
    "",
    response_model=VesselListResponse,
    summary="List and search vessels",
)
async def list_vessels(
    name: str | None = Query(None, description="Partial name match (case-insensitive)"),
    imo: int | None = Query(None, description="Exact IMO number"),
    mmsi: int | None = Query(None, description="Exact MMSI number"),
    vessel_type: str | None = Query(None, description="Vessel type filter"),
    flag: str | None = Query(None, description="Flag state (ISO alpha-3)"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
    db: AsyncSession = Depends(get_db),
) -> VesselListResponse:
    """Return a paginated list of vessels, optionally filtered by search criteria."""
    query = select(Vessel)

    # Apply filters
    if name is not None and name.strip():
        query = query.where(Vessel.name.ilike(f"%{name.strip()}%"))
    if imo is not None:
        query = query.where(Vessel.imo == imo)
    if mmsi is not None:
        query = query.where(Vessel.mmsi == mmsi)
    if vessel_type is not None and vessel_type.strip():
        query = query.where(Vessel.vessel_type.ilike(f"%{vessel_type.strip()}%"))
    if flag is not None and flag.strip():
        query = query.where(Vessel.flag == flag.strip().upper())

    # Count total matches
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.order_by(Vessel.name).offset(offset).limit(per_page)

    result = await db.execute(query)
    vessels = result.scalars().all()

    return VesselListResponse(
        items=[VesselResponse.model_validate(v) for v in vessels],
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 0,
    )


@router.get(
    "/{imo}",
    response_model=VesselResponse,
    summary="Get vessel by IMO number",
)
async def get_vessel(
    imo: int,
    db: AsyncSession = Depends(get_db),
) -> VesselResponse:
    """Retrieve a single vessel by its IMO number.

    Raises:
        HTTPException 404: If no vessel with the given IMO exists.
    """
    result = await db.execute(select(Vessel).where(Vessel.imo == imo))
    vessel = result.scalar_one_or_none()

    if vessel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vessel with IMO {imo} not found",
        )

    return VesselResponse.model_validate(vessel)
