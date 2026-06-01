"""
WebSocket endpoint for live vessel position streaming.

Route::

    WS  /ws/vessels  — live vessel position broadcast

Clients can send a JSON message to set a bounding-box filter::

    {"bbox": [min_lon, min_lat, max_lon, max_lat]}

Send ``{"bbox": null}`` to clear the filter and receive all positions.
"""

import json
import logging
from dataclasses import dataclass, field

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


@dataclass
class ClientConnection:
    """State tracked per connected WebSocket client."""

    websocket: WebSocket
    bbox: list[float] | None = None


class ConnectionManager:
    """Manages WebSocket connections and broadcasts position updates.

    Thread-safety note: FastAPI runs WebSocket handlers on the asyncio
    event loop, so no locks are needed for the connection set.
    """

    def __init__(self) -> None:
        self._connections: dict[int, ClientConnection] = {}

    async def connect(self, websocket: WebSocket) -> ClientConnection:
        """Accept a new WebSocket connection and register it.

        Args:
            websocket: The incoming WebSocket connection.

        Returns:
            A new ``ClientConnection`` tracking the client state.
        """
        await websocket.accept()
        client = ClientConnection(websocket=websocket)
        self._connections[id(websocket)] = client
        logger.info("WebSocket client connected. Total: %d", len(self._connections))
        return client

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a disconnected client.

        Args:
            websocket: The disconnected WebSocket.
        """
        self._connections.pop(id(websocket), None)
        logger.info("WebSocket client disconnected. Total: %d", len(self._connections))

    def update_bbox(self, websocket: WebSocket, bbox: list[float] | None) -> None:
        """Update the bounding-box filter for a client.

        Args:
            websocket: The client's WebSocket.
            bbox: New bounding box ``[min_lon, min_lat, max_lon, max_lat]``
                or ``None`` to clear.
        """
        client = self._connections.get(id(websocket))
        if client is not None:
            client.bbox = bbox

    async def broadcast(self, position_data: dict) -> None:
        """Send a position update to all connected clients that match filters.

        Args:
            position_data: Position dict with at least ``latitude`` and
                ``longitude`` keys.
        """
        lat = position_data.get("latitude")
        lon = position_data.get("longitude")
        message = json.dumps(position_data)

        disconnected: list[int] = []

        for ws_id, client in self._connections.items():
            # Apply bounding box filter
            if client.bbox is not None and lat is not None and lon is not None:
                min_lon, min_lat, max_lon, max_lat = client.bbox
                if not (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon):
                    continue

            try:
                await client.websocket.send_text(message)
            except Exception:
                disconnected.append(ws_id)

        # Clean up broken connections
        for ws_id in disconnected:
            self._connections.pop(ws_id, None)

    @property
    def active_connections(self) -> int:
        """Return the number of currently connected clients."""
        return len(self._connections)


# Singleton manager instance
manager = ConnectionManager()


@router.websocket("/ws/vessels")
async def vessel_position_stream(websocket: WebSocket) -> None:
    """WebSocket endpoint for streaming live vessel positions.

    On connect, the server begins forwarding position updates.
    The client can send JSON messages to configure filters::

        {"bbox": [min_lon, min_lat, max_lon, max_lat]}
        {"bbox": null}   // clear filter
    """
    client = await manager.connect(websocket)

    try:
        while True:
            # Listen for filter updates from the client
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
                if "bbox" in data:
                    bbox = data["bbox"]
                    if bbox is not None:
                        if not (isinstance(bbox, list) and len(bbox) == 4):
                            await websocket.send_text(
                                json.dumps({"error": "bbox must be [min_lon, min_lat, max_lon, max_lat]"})
                            )
                            continue
                        bbox = [float(v) for v in bbox]
                    manager.update_bbox(websocket, bbox)
                    await websocket.send_text(
                        json.dumps({"status": "filter_updated", "bbox": bbox})
                    )
            except (json.JSONDecodeError, ValueError, TypeError) as exc:
                await websocket.send_text(
                    json.dumps({"error": f"Invalid message: {exc}"})
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
        logger.exception("WebSocket error")
