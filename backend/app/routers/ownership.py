"""
Ownership graph endpoint.

Routes::

    GET  /api/vessels/{imo}/ownership  — ownership graph (D3 nodes + edges)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.ownership import OwnershipEdge, OwnershipEntity
from app.models.vessel import Vessel
from app.schemas.ownership import (
    OwnershipEdgeResponse,
    OwnershipEntityResponse,
    OwnershipGraphResponse,
)

router = APIRouter(prefix="/api/vessels", tags=["Ownership"])


@router.get(
    "/{imo}/ownership",
    response_model=OwnershipGraphResponse,
    summary="Get ownership graph for a vessel",
)
async def get_ownership_graph(
    imo: int,
    db: AsyncSession = Depends(get_db),
) -> OwnershipGraphResponse:
    """Return the ownership graph for a vessel as nodes + edges for D3 force-directed layout.

    Traverses all edges linked to the vessel (directly or through entity chains)
    and collects the full set of related entities.

    Raises:
        HTTPException 404: If the vessel does not exist.
    """
    # Verify vessel exists
    vessel_result = await db.execute(select(Vessel).where(Vessel.imo == imo))
    vessel = vessel_result.scalar_one_or_none()

    if vessel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vessel with IMO {imo} not found",
        )

    # Get all edges related to this vessel
    edges_result = await db.execute(
        select(OwnershipEdge).where(OwnershipEdge.vessel_imo == imo)
    )
    edges = list(edges_result.scalars().all())

    # Collect all entity IDs from the edges
    entity_ids: set[int] = set()
    for edge in edges:
        entity_ids.add(edge.source_entity_id)
        entity_ids.add(edge.target_entity_id)

    # Also include edges between the discovered entities (multi-hop chains)
    if entity_ids:
        chain_edges_result = await db.execute(
            select(OwnershipEdge).where(
                or_(
                    OwnershipEdge.source_entity_id.in_(entity_ids),
                    OwnershipEdge.target_entity_id.in_(entity_ids),
                )
            )
        )
        chain_edges = list(chain_edges_result.scalars().all())

        # Merge edge sets (deduplicate by id)
        edge_ids = {e.id for e in edges}
        for ce in chain_edges:
            if ce.id not in edge_ids:
                edges.append(ce)
                edge_ids.add(ce.id)
                entity_ids.add(ce.source_entity_id)
                entity_ids.add(ce.target_entity_id)

    # Fetch all related entities
    nodes: list[OwnershipEntityResponse] = []
    if entity_ids:
        entities_result = await db.execute(
            select(OwnershipEntity)
            .where(OwnershipEntity.id.in_(entity_ids))
            .order_by(OwnershipEntity.id)
        )
        entities = entities_result.scalars().all()
        nodes = [OwnershipEntityResponse.model_validate(e) for e in entities]

    sorted_edges = sorted(edges, key=lambda e: e.id if e.id is not None else 0)

    return OwnershipGraphResponse(
        vessel_imo=imo,
        nodes=nodes,
        edges=[OwnershipEdgeResponse.model_validate(e) for e in sorted_edges],
    )
