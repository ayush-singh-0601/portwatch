"""
Unit tests for app.routers.ws (ConnectionManager & bbox filtering).
"""

from unittest.mock import AsyncMock, MagicMock
import pytest

from app.routers.ws import ClientConnection, ConnectionManager


class TestConnectionManager:
    def test_position_in_bbox_inside(self):
        bbox = [100.0, 1.0, 105.0, 5.0]
        pos = {"latitude": 2.5, "longitude": 102.5}
        assert ConnectionManager._position_in_bbox(pos, bbox) is True

    def test_position_in_bbox_outside(self):
        bbox = [100.0, 1.0, 105.0, 5.0]
        pos = {"latitude": 10.0, "longitude": 102.5}
        assert ConnectionManager._position_in_bbox(pos, bbox) is False

    def test_position_in_bbox_none_coords_defaults_true(self):
        bbox = [100.0, 1.0, 105.0, 5.0]
        pos = {"latitude": None, "longitude": None}
        assert ConnectionManager._position_in_bbox(pos, bbox) is True

    def test_position_in_bbox_antimeridian_crossing(self):
        bbox = [170.0, -10.0, -170.0, 10.0]
        assert ConnectionManager._position_in_bbox({"latitude": 0.0, "longitude": 175.0}, bbox) is True
        assert ConnectionManager._position_in_bbox({"latitude": 0.0, "longitude": -175.0}, bbox) is True
        assert ConnectionManager._position_in_bbox({"latitude": 0.0, "longitude": 150.0}, bbox) is False
        assert ConnectionManager._position_in_bbox({"latitude": 0.0, "longitude": -150.0}, bbox) is False

    def test_filter_payload_for_client_unfiltered(self):
        manager = ConnectionManager()
        client = ClientConnection(websocket=MagicMock(), bbox=None)
        payload = {"type": "position_update", "data": {"lat": 1.5, "lon": 103.5}}
        filtered = manager._filter_payload_for_client(payload, client)
        assert filtered is payload

    def test_filter_payload_for_client_in_bbox(self):
        manager = ConnectionManager()
        client = ClientConnection(websocket=MagicMock(), bbox=[100.0, 1.0, 105.0, 5.0])
        payload = {"type": "position_update", "data": {"lat": 1.5, "lon": 103.5}}
        filtered = manager._filter_payload_for_client(payload, client)
        assert filtered is not None

    def test_filter_payload_for_client_out_of_bbox(self):
        manager = ConnectionManager()
        client = ClientConnection(websocket=MagicMock(), bbox=[100.0, 1.0, 105.0, 5.0])
        payload = {"type": "position_update", "data": {"lat": 25.0, "lon": 55.0}}
        filtered = manager._filter_payload_for_client(payload, client)
        assert filtered is None

    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self):
        manager = ConnectionManager()
        ws = MagicMock()
        ws.accept = AsyncMock()
        client = await manager.connect(ws)
        assert manager.active_connections == 1

        manager.update_bbox(ws, [100.0, 1.0, 105.0, 5.0])
        assert client.bbox == [100.0, 1.0, 105.0, 5.0]

        manager.disconnect(ws)
        assert manager.active_connections == 0
        # Idempotent disconnect
        manager.disconnect(ws)
        assert manager.active_connections == 0

    @pytest.mark.asyncio
    async def test_broadcast_disconnected_client_cleanup(self):
        manager = ConnectionManager()
        ws_good = MagicMock()
        ws_good.accept = AsyncMock()
        ws_good.send_text = AsyncMock()

        ws_broken = MagicMock()
        ws_broken.accept = AsyncMock()
        ws_broken.send_text = AsyncMock(side_effect=RuntimeError("Connection closed"))

        await manager.connect(ws_good)
        await manager.connect(ws_broken)
        assert manager.active_connections == 2

        payload = {"type": "position_update", "data": {"lat": 1.5, "lon": 103.5}}
        await manager.broadcast(payload)

        # Broken client should have been cleaned up
        assert manager.active_connections == 1
        ws_good.send_text.assert_awaited_once()

