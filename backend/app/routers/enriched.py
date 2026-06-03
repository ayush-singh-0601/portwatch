"""
Enriched vessel endpoint that merges vessel data with latest position,
risk score, ownership, and sanctions into the shape the frontend expects.

Route::

    GET  /api/vessels/enriched  — all vessels with embedded real-time data
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.ownership import OwnershipEdge, OwnershipEntity
from app.models.position import VesselPosition
from app.models.risk_score import RiskFactor, RiskScore
from app.models.sanctions import SanctionsEntry, SanctionsMatch
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


@router.get(
    "/enriched",
    summary="Get all vessels with embedded position, risk, ownership, and sanctions",
)
async def get_enriched_vessels(
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Return a flat JSON array of enriched vessel objects.

    Each vessel includes the latest position, risk score with factors,
    ownership chain (registeredOwner / beneficialOwner / operator),
    and sanctions screening results.  The shape matches exactly what
    the React frontend components expect.
    """
    # ── 1. Fetch all vessels ─────────────────────────────────────
    vessel_result = await db.execute(select(Vessel))
    vessels = list(vessel_result.scalars().all())

    # Collect all IMOs and MMSIs
    imo_list = [v.imo for v in vessels]
    mmsi_list = [v.mmsi for v in vessels if v.mmsi is not None]

    # ── 2. Latest position per MMSI (single query for ALL MMSIs) ──
    latest_positions: dict[int, VesselPosition] = {}
    pos_query = (
        select(VesselPosition)
        .distinct(VesselPosition.mmsi)
        .order_by(VesselPosition.mmsi, VesselPosition.time.desc())
    )
    pos_result = await db.execute(pos_query)
    for pos in pos_result.scalars().all():
        latest_positions[pos.mmsi] = pos

    # ── 3. Latest risk score per vessel (single query) ────────────
    risk_scores: dict[int, RiskScore] = {}
    if imo_list:
        latest_risk_sub = (
            select(
                RiskScore.vessel_imo,
                func.max(RiskScore.id).label("max_id"),
            )
            .where(RiskScore.vessel_imo.in_(imo_list))
            .group_by(RiskScore.vessel_imo)
            .subquery()
        )
        risk_query = (
            select(RiskScore)
            .join(latest_risk_sub, RiskScore.id == latest_risk_sub.c.max_id)
            .options(selectinload(RiskScore.factors))
        )
        risk_result = await db.execute(risk_query)
        for rs in risk_result.scalars().all():
            risk_scores[rs.vessel_imo] = rs

    # ── 4. Ownership per vessel ───────────────────────────────────
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
        edges = list(edges_result.scalars().all())

        for edge in edges:
            imo = edge.vessel_imo
            if imo not in ownership_map:
                ownership_map[imo] = {
                    "registeredOwner": None,
                    "beneficialOwner": None,
                    "operator": None,
                    "flagHistory": [],
                }
            rel = (edge.relationship_type or "").lower()
            entity_name = edge.target_entity.name if edge.target_entity else None
            if "owner" in rel and "beneficial" not in rel:
                ownership_map[imo]["registeredOwner"] = entity_name
            elif "beneficial" in rel:
                ownership_map[imo]["beneficialOwner"] = entity_name
            elif "operator" in rel or "manager" in rel:
                ownership_map[imo]["operator"] = entity_name

    # ── 5. Sanctions per vessel ───────────────────────────────────
    sanctions_map: dict[int, dict] = {}
    if imo_list:
        matches_result = await db.execute(
            select(SanctionsMatch)
            .where(SanctionsMatch.vessel_imo.in_(imo_list))
            .options(selectinload(SanctionsMatch.sanctions_entry))
        )
        matches = list(matches_result.scalars().all())

        for match in matches:
            imo = match.vessel_imo
            if imo not in sanctions_map:
                sanctions_map[imo] = {"matched": False, "lists": []}

            entry = match.sanctions_entry
            sanctions_map[imo]["lists"].append({
                "name": f"{entry.source} — {entry.entity_name}" if entry else "Unknown",
                "matchType": match.match_type or "fuzzy",
                "confidence": round(match.match_score / 100.0, 2),
            })
            if match.match_score >= 85.0:
                sanctions_map[imo]["matched"] = True

    # ── 6. Assemble enriched response ─────────────────────────────
    enriched: list[dict] = []
    registered_mmsis = set()

    for vessel in vessels:
        if vessel.mmsi is not None:
            registered_mmsis.add(vessel.mmsi)

        # Position
        pos = latest_positions.get(vessel.mmsi) if vessel.mmsi else None

        # Risk
        risk = risk_scores.get(vessel.imo)
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

        # Sanctions (default if not found)
        sanctions = sanctions_map.get(vessel.imo, {"matched": False, "lists": []})

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
    for mmsi, pos in latest_positions.items():
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
