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
