"""
Pydantic schemas for the ownership graph (D3 visualisation).
"""

from datetime import date, datetime

from pydantic import BaseModel, Field


class OwnershipEntityResponse(BaseModel):
    """A node in the ownership graph."""

    id: int
    name: str
    entity_type: str | None = None
    country: str | None = None
    registration: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OwnershipEdgeResponse(BaseModel):
    """A directed edge in the ownership graph."""

    id: int
    source_entity_id: int = Field(..., description="ID of the source node")
    target_entity_id: int = Field(..., description="ID of the target node")
    relationship_type: str | None = None
    vessel_imo: int | None = None
    effective_date: date | None = None
    end_date: date | None = None

    model_config = {"from_attributes": True}


class OwnershipGraphResponse(BaseModel):
    """Complete ownership graph payload formatted for D3 force-directed graph.

    ``nodes`` maps to D3 nodes and ``edges`` maps to D3 links.
    """

    vessel_imo: int
    nodes: list[OwnershipEntityResponse]
    edges: list[OwnershipEdgeResponse]
