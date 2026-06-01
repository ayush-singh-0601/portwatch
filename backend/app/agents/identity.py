"""
IdentityResolutionAgent — resolves vessel identity and ownership chain.

Given an IMO number, resolves the full corporate ownership structure
from available data sources (IMO GISIS, manual entry, or API).
Builds a NetworkX graph for chain traversal and cycle detection.
"""

import logging
from datetime import datetime, timezone

import networkx as nx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ownership import OwnershipEdge, OwnershipEntity
from app.models.vessel import Vessel

logger = logging.getLogger(__name__)


class IdentityResolutionAgent:
    """Resolves vessel identity and builds ownership graphs.

    Usage::

        agent = IdentityResolutionAgent(db_session)
        graph = await agent.resolve(imo=9811000)
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def resolve(self, imo: int) -> dict:
        """Resolve the full identity and ownership chain for a vessel.

        Args:
            imo: IMO number of the vessel.

        Returns:
            Dict with keys: vessel, entities, edges, graph_data (D3 format).
        """
        vessel = await self.db.get(Vessel, imo)
        if not vessel:
            logger.warning("Vessel IMO %d not found", imo)
            return {"vessel": None, "entities": [], "edges": [], "graph_data": None}

        # Load ownership entities and edges for this vessel
        edges_result = await self.db.execute(
            select(OwnershipEdge).where(OwnershipEdge.vessel_imo == imo)
        )
        edges = list(edges_result.scalars().all())

        # Collect all entity IDs
        entity_ids = set()
        for edge in edges:
            entity_ids.add(edge.source_entity_id)
            entity_ids.add(edge.target_entity_id)

        entities = []
        if entity_ids:
            entities_result = await self.db.execute(
                select(OwnershipEntity).where(OwnershipEntity.id.in_(entity_ids))
            )
            entities = list(entities_result.scalars().all())

        # Build NetworkX graph
        G = self._build_graph(vessel, entities, edges)

        # Check for anomalies
        anomalies = self._detect_anomalies(G, vessel)

        # Build D3 visualization data
        graph_data = self._to_d3_format(vessel, entities, edges, anomalies)

        logger.info(
            "Resolved IMO %d: %d entities, %d edges, %d anomalies",
            imo, len(entities), len(edges), len(anomalies),
        )

        return {
            "vessel": vessel,
            "entities": entities,
            "edges": edges,
            "anomalies": anomalies,
            "graph_data": graph_data,
        }

    def _build_graph(
        self,
        vessel: Vessel,
        entities: list[OwnershipEntity],
        edges: list[OwnershipEdge],
    ) -> nx.DiGraph:
        """Build a directed graph of the ownership chain."""
        G = nx.DiGraph()

        # Add vessel as the root node
        G.add_node(
            f"vessel_{vessel.imo}",
            label=vessel.name,
            node_type="vessel",
            imo=vessel.imo,
        )

        # Add entity nodes
        for entity in entities:
            G.add_node(
                f"entity_{entity.id}",
                label=entity.name,
                node_type=entity.entity_type or "company",
                country=entity.country,
            )

        # Add edges
        for edge in edges:
            G.add_edge(
                f"entity_{edge.source_entity_id}",
                f"entity_{edge.target_entity_id}",
                relationship=edge.relationship_type,
                vessel_imo=edge.vessel_imo,
            )
            # Also link entities to the vessel
            if edge.relationship_type in ("registered_owner", "owner"):
                G.add_edge(
                    f"entity_{edge.source_entity_id}",
                    f"vessel_{vessel.imo}",
                    relationship=edge.relationship_type,
                )

        return G

    def _detect_anomalies(self, G: nx.DiGraph, vessel: Vessel) -> list[dict]:
        """Detect anomalies in the ownership structure."""
        anomalies = []

        # Circular ownership
        cycles = list(nx.simple_cycles(G))
        for cycle in cycles:
            anomalies.append({
                "type": "circular_ownership",
                "severity": "high",
                "description": f"Circular ownership detected: {' → '.join(cycle)}",
                "nodes": cycle,
            })

        # Excessive depth (> 5 layers)
        vessel_node = f"vessel_{vessel.imo}"
        if vessel_node in G:
            for node in G.nodes:
                if node != vessel_node and nx.has_path(G, node, vessel_node):
                    path = nx.shortest_path(G, node, vessel_node)
                    if len(path) > 5:
                        anomalies.append({
                            "type": "deep_ownership",
                            "severity": "medium",
                            "description": f"Ownership chain has {len(path)} layers",
                            "nodes": path,
                        })

        # Flag changes (from vessel history)
        if vessel.year_built and (datetime.now().year - vessel.year_built) > 20:
            anomalies.append({
                "type": "aged_vessel",
                "severity": "low",
                "description": f"Vessel is {datetime.now().year - vessel.year_built} years old",
            })

        return anomalies

    def _to_d3_format(
        self,
        vessel: Vessel,
        entities: list[OwnershipEntity],
        edges: list[OwnershipEdge],
        anomalies: list[dict],
    ) -> dict:
        """Convert ownership data to D3 force-directed graph format.

        Returns:
            Dict with 'nodes' and 'links' arrays for D3.js consumption.
        """
        nodes = []
        links = []

        # Vessel node (center)
        nodes.append({
            "id": f"vessel_{vessel.imo}",
            "label": vessel.name,
            "type": "vessel",
            "imo": vessel.imo,
            "flag": vessel.flag,
            "isCenter": True,
        })

        # Entity nodes
        for entity in entities:
            nodes.append({
                "id": f"entity_{entity.id}",
                "label": entity.name,
                "type": entity.entity_type or "company",
                "country": entity.country,
                "isCenter": False,
            })

        # Edge links
        for edge in edges:
            links.append({
                "source": f"entity_{edge.source_entity_id}",
                "target": f"entity_{edge.target_entity_id}",
                "relationship": edge.relationship_type or "related",
            })

            # Direct link to vessel for owners
            if edge.relationship_type in ("registered_owner", "owner", "operator", "ism_manager"):
                links.append({
                    "source": f"entity_{edge.source_entity_id}",
                    "target": f"vessel_{vessel.imo}",
                    "relationship": edge.relationship_type,
                })

        return {
            "nodes": nodes,
            "links": links,
            "anomalies": anomalies,
        }

    async def add_ownership_entity(
        self,
        name: str,
        entity_type: str = "company",
        country: str | None = None,
        registration: str | None = None,
    ) -> OwnershipEntity:
        """Add a new ownership entity to the database."""
        entity = OwnershipEntity(
            name=name,
            entity_type=entity_type,
            country=country,
            registration=registration,
        )
        self.db.add(entity)
        await self.db.commit()
        await self.db.refresh(entity)
        return entity

    async def add_ownership_edge(
        self,
        source_entity_id: int,
        target_entity_id: int,
        relationship_type: str,
        vessel_imo: int,
    ) -> OwnershipEdge:
        """Add a directed ownership relationship."""
        edge = OwnershipEdge(
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            relationship_type=relationship_type,
            vessel_imo=vessel_imo,
        )
        self.db.add(edge)
        await self.db.commit()
        await self.db.refresh(edge)
        return edge
