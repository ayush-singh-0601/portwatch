"""
Enriched vessel endpoint that merges vessel data with latest position,
risk score, ownership, and sanctions into the shape the frontend expects.

Route::

    GET  /api/vessels/enriched  — all vessels with embedded real-time data
"""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.ownership import OwnershipEdge
from app.models.position import VesselPosition
from app.models.risk_score import RiskScore
from app.models.sanctions import SanctionsMatch
from app.models.vessel import Vessel
from app.utils.flag_lookup import get_flag_info

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vessels", tags=["Vessels"])


def _vessel_type_normalise(raw: str | None) -> str:
    """Normalise vessel_type to the frontend's expected lowercase keys."""
    if not raw:
        return "other"
    lower = raw.strip().lower()
    # Map common database values to frontend keys
    mapping = {
        "cargo": "cargo",
        "bulk carrier": "cargo",
        "container": "cargo",
        "general cargo": "cargo",
        "tanker": "tanker",
        "oil tanker": "tanker",
        "chemical tanker": "tanker",
        "lng tanker": "tanker",
        "crude oil tanker": "tanker",
        "fishing": "fishing",
        "trawler": "fishing",
        "passenger": "passenger",
        "cruise": "passenger",
        "ferry": "passenger",
        "ro-ro": "passenger",
        "military": "military",
        "naval": "military",
        "special / tug": "other",
    }
    return mapping.get(lower, "other")


def _resolve_ownership_from_edges(edges: list) -> dict:
    """Build an ownership dict from a list of OwnershipEdge ORM objects.

    Iterates over all edges for a single vessel and maps relationship types
    to the three display fields expected by the frontend.

    Args:
        edges: List of ``OwnershipEdge`` objects (already with loaded
            ``source_entity`` and ``target_entity`` relationships).

    Returns:
        A dict with keys ``registeredOwner``, ``beneficialOwner``,
        ``operator``, and ``flagHistory``.
    """
    result: dict = {
        "registeredOwner": None,
        "beneficialOwner": None,
        "operator": None,
        "flagHistory": [],
    }
    for edge in edges:
        rel = (edge.relationship_type or "").lower()
        entity_name = edge.target_entity.name if edge.target_entity else None
        if "beneficial" in rel:
            result["beneficialOwner"] = entity_name
        elif "owner" in rel:
            result["registeredOwner"] = entity_name
        elif "operator" in rel or "manager" in rel:
            result["operator"] = entity_name
    return result


@router.get(
    "/enriched",
    summary="Get all vessels with embedded position, risk, ownership, and sanctions",
)
async def get_enriched_vessels(
    limit: int = Query(
        1000,
        ge=1,
        le=5000,
        description="Maximum number of enriched vessels to return",
    ),
    active_minutes: int = Query(
        720,
        ge=0,
        le=43200,
        description="Only include latest positions newer than this many minutes; 0 disables the age filter",
    ),
    include_unregistered: bool = Query(
        True,
        description="Include MMSI-only AIS positions that do not yet have a registered vessel record",
    ),
    include_inactive_registered: bool = Query(
        False,
        description="Include registered vessels even when they have no active/latest position",
    ),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return a flat JSON array of enriched vessel objects.

    Each vessel includes the latest position, risk score with factors,
    ownership chain (registeredOwner / beneficialOwner / operator),
    and sanctions screening results.  The shape matches exactly what
    the React frontend components expect.
    """
    # ── 1. Fetch all vessels with eager-loaded relationships ──────
    cutoff = (
        datetime.now(timezone.utc) - timedelta(minutes=active_minutes)
        if active_minutes > 0
        else None
    )

    # Collect all IMOs
    latest_times_query = select(
        VesselPosition.mmsi,
        func.max(VesselPosition.time).label("latest_time"),
    ).group_by(VesselPosition.mmsi)
    if cutoff is not None:
        latest_times_query = latest_times_query.where(VesselPosition.time >= cutoff)

    latest_times = latest_times_query.subquery()

    # ── 2. Latest position per MMSI (single query for ALL MMSIs) ──
    latest_positions: dict[int, VesselPosition] = {}
    pos_query = (
        select(VesselPosition)
        .join(
            latest_times,
            and_(
                VesselPosition.mmsi == latest_times.c.mmsi,
                VesselPosition.time == latest_times.c.latest_time,
            ),
        )
        .order_by(VesselPosition.time.desc())
        .limit(limit)
    )
    pos_result = await db.execute(pos_query)
    for pos in pos_result.scalars().all():
        latest_positions[pos.mmsi] = pos

    active_mmsis = list(latest_positions)
    vessel_query = select(Vessel).options(
        selectinload(Vessel.risk_scores).selectinload(RiskScore.factors),
        selectinload(Vessel.port_calls),
        selectinload(Vessel.sanctions_matches).selectinload(SanctionsMatch.sanctions_entry),
    )

    if include_inactive_registered or not active_mmsis:
        if active_mmsis:
            vessel_query = vessel_query.where(
                or_(Vessel.mmsi.in_(active_mmsis), Vessel.mmsi.is_(None))
            )
        vessel_query = vessel_query.order_by(Vessel.updated_at.desc()).limit(limit)
    else:
        vessel_query = vessel_query.where(Vessel.mmsi.in_(active_mmsis)).limit(limit)

    vessel_result = await db.execute(vessel_query)
    vessels = list(vessel_result.scalars().all())
    imo_list = [v.imo for v in vessels]

    # ── 3. Ownership per vessel (single query for edges) ──────────
    ownership_map: dict[int, dict] = {}
    if imo_list:
        edges_result = await db.execute(
            select(OwnershipEdge)
            .where(OwnershipEdge.vessel_imo.in_(imo_list))
            .options(
                selectinload(OwnershipEdge.source_entity),
                selectinload(OwnershipEdge.target_entity),
            )
        )
        all_edges = list(edges_result.scalars().all())

        # Group edges by vessel IMO then resolve with the shared helper.
        edges_by_imo: dict[int, list] = {}
        for edge in all_edges:
            edges_by_imo.setdefault(edge.vessel_imo, []).append(edge)

        for imo, vessel_edges in edges_by_imo.items():
            ownership_map[imo] = _resolve_ownership_from_edges(vessel_edges)

    # ── 4. Assemble enriched response ─────────────────────────────
    enriched: list[dict] = []
    registered_mmsis = set()

    for vessel in vessels:
        if vessel.mmsi is not None:
            registered_mmsis.add(vessel.mmsi)

        # Position
        pos = latest_positions.get(vessel.mmsi) if vessel.mmsi else None

        # Risk (latest score — ordered by when it was calculated, not by
        # primary key, so a manually triggered recalculation is always preferred
        # over an older score with a higher auto-increment id).
        risk = (
            max(vessel.risk_scores, key=lambda x: x.calculated_at)
            if vessel.risk_scores
            else None
        )
        risk_score_val = risk.total_score if risk else 0
        risk_factors = []
        if risk and risk.factors:
            risk_factors = [
                {
                    "factor_name": f.factor_name,
                    "points": f.points,
                    "evidence_description": f.evidence_description or "",
                }
                for f in risk.factors
            ]

        # Flag
        flag_info = get_flag_info(vessel.flag)

        # Ownership (default if not found)
        ownership = ownership_map.get(vessel.imo, {
            "registeredOwner": None,
            "beneficialOwner": None,
            "operator": None,
            "flagHistory": [],
        })

        # Sanctions (build from eager loaded matches)
        sanctions = {"matched": False, "lists": []}
        for match in vessel.sanctions_matches:
            entry = match.sanctions_entry
            sanctions["lists"].append({
                "name": f"{entry.source} — {entry.entity_name}" if entry else "Unknown",
                "matchType": match.match_type or "fuzzy",
                "confidence": round(match.match_score / 100.0, 2),
            })
            if match.match_score >= 85.0:
                sanctions["matched"] = True

        # Port calls
        port_calls_list = []
        if vessel.port_calls:
            # Sort by arrival time desc
            sorted_pcs = sorted(
                vessel.port_calls,
                key=lambda x: x.arrival_time if x.arrival_time else datetime.min.replace(tzinfo=timezone.utc),
                reverse=True
            )
            for pc in sorted_pcs:
                port_calls_list.append({
                    "id": pc.id,
                    "portName": pc.port_name,
                    "portCountry": pc.port_country,
                    "unlocode": pc.unlocode,
                    "arrivalTime": pc.arrival_time.isoformat() if pc.arrival_time else None,
                    "departureTime": pc.departure_time.isoformat() if pc.departure_time else None,
                    "pscDetention": pc.psc_detention,
                    "pscDeficiencies": pc.psc_deficiencies,
                })

        enriched.append({
            "id": str(vessel.imo),
            "imo": str(vessel.imo),
            "mmsi": str(vessel.mmsi) if vessel.mmsi else None,
            "callSign": vessel.call_sign,
            "name": vessel.name,
            "type": _vessel_type_normalise(vessel.vessel_type),
            "flag": flag_info,
            "riskScore": risk_score_val,
            "riskFactors": risk_factors,
            "position": {
                "lat": pos.latitude,
                "lon": pos.longitude,
            } if pos else None,
            "heading": pos.heading if pos else 0,
            "speed": pos.speed if pos else 0,
            "grossTonnage": vessel.gross_tonnage,
            "deadweight": vessel.dwt,
            "yearBuilt": vessel.year_built,
            "length": None,   # Not in DB schema
            "beam": None,     # Not in DB schema
            "lastSeen": pos.time.isoformat() if pos else vessel.updated_at.isoformat(),
            "destination": None,  # Not in DB schema
            "eta": None,          # Not in DB schema
            "ownership": ownership,
            "sanctions": sanctions,
            "portCalls": port_calls_list,
        })

    # Synthesize vessels for positions with no registered vessel
    for mmsi, pos in (latest_positions.items() if include_unregistered else []):
        if len(enriched) >= limit:
            break
        if mmsi not in registered_mmsis:
            flag_info = get_flag_info(None)  # unknown flag
            enriched.append({
                "id": str(mmsi),
                "imo": None,
                "mmsi": str(mmsi),
                "callSign": None,
                "name": f"MMSI {mmsi}",
                "type": "other",
                "flag": flag_info,
                "riskScore": 0,
                "riskFactors": [],
                "position": {
                    "lat": pos.latitude,
                    "lon": pos.longitude,
                },
                "heading": pos.heading or 0,
                "speed": pos.speed or 0,
                "grossTonnage": None,
                "deadweight": None,
                "yearBuilt": None,
                "length": None,
                "beam": None,
                "lastSeen": pos.time.isoformat(),
                "destination": None,
                "eta": None,
                "ownership": {
                    "registeredOwner": None,
                    "beneficialOwner": None,
                    "operator": None,
                    "flagHistory": [],
                },
                "sanctions": {"matched": False, "lists": []},
                "portCalls": [],
            })

    return enriched
