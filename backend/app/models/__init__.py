"""
Models package — imports and re-exports every ORM model so that
``from app.models import Base, Vessel, ...`` works everywhere.

This also ensures Alembic's ``target_metadata = Base.metadata`` picks
up all tables when generating migrations.
"""

from app.models.base import Base
from app.models.dark_event import DarkEvent
from app.models.ownership import OwnershipEdge, OwnershipEntity
from app.models.port import Port
from app.models.port_call import PortCall
from app.models.position import VesselPosition
from app.models.risk_score import RiskFactor, RiskScore
from app.models.sanctions import SanctionsEntry, SanctionsMatch
from app.models.sts_event import STSEvent
from app.models.vessel import Vessel

__all__ = [
    "Base",
    "DarkEvent",
    "OwnershipEdge",
    "OwnershipEntity",
    "Port",
    "PortCall",
    "RiskFactor",
    "RiskScore",
    "SanctionsEntry",
    "SanctionsMatch",
    "STSEvent",
    "Vessel",
    "VesselPosition",
]
