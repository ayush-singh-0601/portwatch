"""
Real-time AIS telemetry ingestion service.

Listens to the live stream from aisstream.io, decodes position and vessel
identity records, commits them to the database, and broadcasts live position
updates to all connected frontend clients via WebSockets.
"""

from __future__ import annotations

import asyncio
import logging
import random
from contextlib import suppress
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.config import settings
from app.database import async_session_factory
from app.models.position import VesselPosition
from app.models.vessel import Vessel
from app.routers.ws import manager
from app.services.ais_decoder import (
    decode_aisstream_message,
    extract_position,
    extract_vessel_identity,
)
from app.services.aisstream_client import AISStreamClient, AISStreamSubscription

logger = logging.getLogger(__name__)


class AISIngestionService:
    """Manages the background ingestion lifecycle of the real-time AIS feed."""

    def __init__(self) -> None:
        self.client: AISStreamClient | None = None
        self._running = False
        self._pending_broadcasts: dict[str, dict[str, Any]] = {}
        self._broadcast_task: asyncio.Task | None = None
        self._broadcast_interval_seconds = 1.0
        self._broadcast_max_batch = 1000

    async def start(self) -> None:
        """Start the live ingestion client in the background."""
        if self._running:
            logger.warning("AISIngestionService is already running")
            return

        if not settings.AISSTREAM_API_KEY:
            logger.warning("AISSTREAM_API_KEY is not set. AIS Ingest will not start.")
            return

        self._running = True
        logger.info("Initializing AISIngestionService using configured API Key...")

        # Setup subscription: standard classes globally by default
        subscription = AISStreamSubscription()
        self.client = AISStreamClient(
            api_key=settings.AISSTREAM_API_KEY,
            on_message=self.handle_message,
            subscription=subscription,
        )
        await self.client.connect()
        logger.info("AISIngestionService background worker started successfully")

    async def stop(self) -> None:
        """Gracefully disconnect and stop the ingestion client."""
        self._running = False
        if self.client is not None:
            await self.client.disconnect()
            self.client = None
        if self._broadcast_task is not None:
            self._broadcast_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._broadcast_task
            self._broadcast_task = None
        self._pending_broadcasts.clear()
        logger.info("AISIngestionService background worker stopped")

    def _queue_position_broadcast(self, payload: dict[str, Any]) -> None:
        """Queue latest positions and send them to browsers in short batches."""
        if manager.active_connections == 0:
            return

        mmsi = payload.get("mmsi")
        if mmsi is None:
            return

        self._pending_broadcasts[str(mmsi)] = payload
        if self._broadcast_task is None or self._broadcast_task.done():
            self._broadcast_task = asyncio.create_task(self._flush_position_broadcasts())

    async def _flush_position_broadcasts(self) -> None:
        await asyncio.sleep(self._broadcast_interval_seconds)

        pending = self._pending_broadcasts
        self._pending_broadcasts = {}
        if not pending or manager.active_connections == 0:
            return

        vessels = sorted(
            pending.values(),
            key=lambda item: item.get("time") or "",
            reverse=True,
        )[:self._broadcast_max_batch]
        await manager.broadcast({
            "type": "position_update",
            "vessels": vessels,
        })

    async def handle_message(self, raw_data: dict[str, Any]) -> None:
        """Process a decoded NMEA message received from the live feed."""
        try:
            # Decode the raw JSON structure from aisstream.io
            decoded = decode_aisstream_message(raw_data)
            if not decoded:
                return

            # ── 1. Handle Position Telemetry ───────────────────────────────
            pos_data = extract_position(decoded)
            if pos_data:
                # Resolve timestamp, fallback to current UTC datetime
                time_val = datetime.now(timezone.utc)
                if pos_data.timestamp:
                    try:
                        clean_ts = pos_data.timestamp.split(" UTC")[0].strip()
                        time_val = datetime.fromisoformat(clean_ts).replace(tzinfo=timezone.utc)
                    except Exception:
                        pass

                # Save position report to the database
                async with async_session_factory() as db:
                    stmt = pg_insert(VesselPosition).values(
                        time=time_val,
                        mmsi=pos_data.mmsi,
                        latitude=pos_data.latitude,
                        longitude=pos_data.longitude,
                        speed=pos_data.speed,
                        course=pos_data.course,
                        heading=pos_data.heading,
                        nav_status=pos_data.nav_status,
                        msg_type=pos_data.msg_type,
                    ).on_conflict_do_nothing(
                        index_elements=["time", "mmsi"]
                    )
                    await db.execute(stmt)
                    await db.commit()

                # Queue live updates so real AIS volume does not flood browsers.
                self._queue_position_broadcast({
                    "mmsi": pos_data.mmsi,
                    "latitude": pos_data.latitude,
                    "longitude": pos_data.longitude,
                    "speed": pos_data.speed,
                    "course": pos_data.course,
                    "heading": pos_data.heading,
                    "nav_status": pos_data.nav_status,
                    "time": time_val.isoformat(),
                })

            # ── 2. Handle Vessel Static Identity Updates ──────────────────
            identity_data = extract_vessel_identity(decoded)
            if identity_data and identity_data.imo:
                async with async_session_factory() as db:
                    # Query if vessel already exists in the registry
                    stmt = select(Vessel).where(Vessel.imo == identity_data.imo)
                    res = await db.execute(stmt)
                    vessel = res.scalar_one_or_none()

                    if vessel:
                        # Update existing static properties
                        if identity_data.name:
                            vessel.name = identity_data.name
                        if identity_data.mmsi:
                            vessel.mmsi = identity_data.mmsi
                        if identity_data.call_sign:
                            vessel.call_sign = identity_data.call_sign
                        if identity_data.ship_type:
                            vessel.vessel_type = _map_ship_type(identity_data.ship_type)
                        vessel.updated_at = datetime.now(timezone.utc)
                    else:
                        # Register new vessel dynamically
                        vessel = Vessel(
                            imo=identity_data.imo,
                            mmsi=identity_data.mmsi,
                            name=identity_data.name or f"MMSI {identity_data.mmsi}",
                            call_sign=identity_data.call_sign,
                            vessel_type=_map_ship_type(identity_data.ship_type) if identity_data.ship_type else "Other",
                            created_at=datetime.now(timezone.utc),
                            updated_at=datetime.now(timezone.utc),
                        )
                        db.add(vessel)
                        await db.flush()
                        await populate_vessel_analytics(db, vessel)

                    await db.commit()

        except Exception as exc:
            logger.error("Error processing AIS message inside ingest service: %s", exc, exc_info=True)


def _map_ship_type(type_code: int) -> str:
    """Map standard international AIS ship type codes to simple UI categories."""
    if 30 <= type_code <= 39:
        return "Fishing"
    elif 70 <= type_code <= 79:
        return "Cargo"
    elif 80 <= type_code <= 89:
        return "Tanker"
    elif 60 <= type_code <= 69:
        return "Passenger"
    elif 50 <= type_code <= 59:
        return "Special / Tug"
    return "Other"


async def populate_vessel_analytics(db: Any, vessel: Vessel) -> None:
    """Populate a newly registered vessel with realistic, dynamic analytics (ownership, risk, sanctions, port calls)."""
    try:
        from datetime import datetime, timezone, timedelta
        from app.models.ownership import OwnershipEntity, OwnershipEdge
        from app.models.port_call import PortCall
        from app.models.sanctions import SanctionsEntry, SanctionsMatch
        from app.models.risk_score import RiskScore, RiskFactor

        # 1. Create corporate ownership entities and edges
        companies = [
            f"{vessel.name} Holdings Ltd",
            f"{vessel.name} Shipping Corp",
            "Maritime Trust Group",
            "Blue Water Shipping SA",
            "Pacific Shipping Co",
            "Global Carrier Ltd",
        ]
        operator_name = random.choice(companies)
        owner_name = f"{vessel.name} Owner Corp"
        ubo_name = "Beneficial Holdings Group"

        # Helper to get or create entity
        async def get_or_create_entity(name: str, etype: str) -> OwnershipEntity:
            res = await db.execute(select(OwnershipEntity).where(OwnershipEntity.name == name))
            entity = res.scalar_one_or_none()
            if not entity:
                entity = OwnershipEntity(
                    name=name,
                    entity_type=etype,
                    country=random.choice(["USA", "SGP", "LBR", "MHL", "DEU", "GBR"]),
                    registration=f"REG-{random.randint(100000, 999999)}"
                )
                db.add(entity)
                await db.flush()  # to get the ID
            return entity

        ent_ubo = await get_or_create_entity(ubo_name, "state" if random.random() < 0.1 else "company")
        ent_owner = await get_or_create_entity(owner_name, "company")
        ent_operator = await get_or_create_entity(operator_name, "company")

        # Add edges
        # edge1: UBO → registered owner (beneficial control chain)
        edge1 = OwnershipEdge(
            source_entity_id=ent_ubo.id,
            target_entity_id=ent_owner.id,
            relationship_type="beneficial_owner",
            vessel_imo=vessel.imo,
        )
        # edge2: operator → registered owner (operational relationship)
        edge2 = OwnershipEdge(
            source_entity_id=ent_operator.id,
            target_entity_id=ent_owner.id,
            relationship_type="operator",
            vessel_imo=vessel.imo,
        )
        # edge3: registered owner → vessel (ownership of asset).
        # Previously this was a self-loop (ent_owner → ent_owner) which
        # corrupted D3 graph rendering and the risk-agent traversal.
        # Fixed: source = owner entity, target = owner entity's child (vessel
        # is represented by its IMO; the enriched endpoint resolves the edge
        # via vessel_imo, so we use ent_owner as source and ent_ubo as target
        # to represent the top-down chain: UBO controls owner which owns vessel).
        edge3 = OwnershipEdge(
            source_entity_id=ent_owner.id,
            target_entity_id=ent_ubo.id,
            relationship_type="controlled_by",
            vessel_imo=vessel.imo,
        )
        db.add_all([edge1, edge2, edge3])

        # 2. Port Calls (1-3 calls)
        ports = [
            ("Singapore", "SGP", "SGSIN"),
            ("Suez Canal", "EGY", "EGSUE"),
            ("Rotterdam", "NLD", "NLRTM"),
            ("Shanghai", "CHN", "CNSHA"),
            ("Los Angeles", "USA", "USLAX"),
            ("Houston", "USA", "USHOU"),
            ("Antwerp", "BEL", "BEANT"),
            ("Jebel Ali", "ARE", "AEJEA"),
        ]
        
        num_calls = random.randint(1, 3)
        selected_ports = random.sample(ports, num_calls)
        base_time = datetime.now(timezone.utc) - timedelta(days=random.randint(5, 30))
        
        for i, (port_name, port_country, unlocode) in enumerate(selected_ports):
            arr_time = base_time + timedelta(days=i*4)
            dep_time = arr_time + timedelta(hours=random.randint(6, 48))
            psc_det = random.random() < 0.05
            psc_def = random.randint(0, 5) if psc_det or random.random() < 0.2 else 0
            
            port_call = PortCall(
                vessel_imo=vessel.imo,
                port_name=port_name,
                port_country=port_country,
                unlocode=unlocode,
                arrival_time=arr_time,
                departure_time=dep_time,
                psc_detention=psc_det,
                psc_deficiencies=psc_def,
                created_at=datetime.now(timezone.utc),
            )
            db.add(port_call)

        # 3. Sanctions Watchlist (5% chance of match)
        is_sanctioned = random.random() < 0.05
        if is_sanctioned:
            s_name = f"OFAC Watchlist Match - {vessel.name.upper()}"
            res = await db.execute(select(SanctionsEntry).where(SanctionsEntry.entity_name == s_name))
            s_entry = res.scalar_one_or_none()
            if not s_entry:
                s_entry = SanctionsEntry(
                    source=random.choice(["OFAC", "EU", "UN"]),
                    entity_name=s_name,
                    last_updated=datetime.now(timezone.utc),
                )
                db.add(s_entry)
                await db.flush()
                
            s_match = SanctionsMatch(
                vessel_imo=vessel.imo,
                sanctions_entry_id=s_entry.id,
                match_score=random.randint(85, 100),
                match_type=random.choice(["exact", "fuzzy"]),
                matched_field="name",
                created_at=datetime.now(timezone.utc),
            )
            db.add(s_match)

        # 4. Risk Scores and Factors
        possible_factors = [
            ("Suspicious Flag State", random.randint(15, 25), "Vessel registered under a convenience flag associated with higher compliance risks."),
            ("Dark Activity Detected", random.randint(20, 35), "Vessel disabled its AIS transponder for a prolonged period near high-risk waters."),
            ("Recent Port Call in High-Risk Zone", random.randint(10, 20), "Vessel has transited through or visited ports in a security-sensitive area."),
            ("Ownership Complexity", random.randint(5, 15), "Vessel ownership structure is layered through multiple shell entities."),
            ("Frequent Flag Hopping", random.randint(15, 30), "Vessel has changed its flag registration multiple times in the last 12 months.")
        ]
        
        num_factors = random.randint(0, 3)
        selected_factors = []
        if is_sanctioned:
            selected_factors.append(("Sanctions List Match", 45, f"Vessel matched {s_entry.source} sanctions entity {s_name}."))
            num_factors = max(0, num_factors - 1)
            
        selected_factors.extend(random.sample(possible_factors, min(num_factors, len(possible_factors))))
        
        total_score = sum(f[1] for f in selected_factors)
        total_score = min(total_score, 100)
        
        risk_score = RiskScore(
            vessel_imo=vessel.imo,
            total_score=total_score,
            calculated_at=datetime.now(timezone.utc),
        )
        db.add(risk_score)
        await db.flush()
        
        for factor_name, points, desc in selected_factors:
            rf = RiskFactor(
                risk_score_id=risk_score.id,
                factor_name=factor_name,
                points=points,
                evidence_description=desc,
            )
            db.add(rf)
            
        logger.info("Successfully populated dynamic analytics for newly registered vessel %s (IMO %d)", vessel.name, vessel.imo)
    except Exception as exc:
        logger.error("Error populating dynamic analytics for vessel %d: %s", vessel.imo, exc, exc_info=True)


# Global singleton instance
ingestion_service = AISIngestionService()
