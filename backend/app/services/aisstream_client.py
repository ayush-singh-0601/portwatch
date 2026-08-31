"""
Async WebSocket client for aisstream.io.

Connects to the aisstream.io live AIS data feed, manages subscriptions,
and dispatches decoded messages via callbacks.

Usage::

    from app.services.aisstream_client import AISStreamClient

    async def on_message(data: dict):
        print(data)

    client = AISStreamClient(api_key="...", on_message=on_message)
    await client.connect()
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import websockets
from websockets.asyncio.client import ClientConnection

logger = logging.getLogger(__name__)

# aisstream.io WebSocket endpoint
AISSTREAM_WS_URL = "wss://stream.aisstream.io/v0/stream"

# Reconnection parameters
INITIAL_BACKOFF_SECS = 1.0
MAX_BACKOFF_SECS = 60.0
BACKOFF_MULTIPLIER = 2.0
JITTER_MAX_SECS = 2.0


@dataclass
class AISStreamSubscription:
    """Subscription configuration for aisstream.io.

    Attributes:
        bounding_boxes: List of ``[[lat_min, lon_min], [lat_max, lon_max]]`` pairs.
        filter_message_types: AIS message types to receive
            (e.g. ``["PositionReport", "ShipStaticData"]``).
    """

    bounding_boxes: list[list[list[float]]] = field(default_factory=lambda: [
        [[-90, -180], [90, 180]],  # Global by default
    ])
    filter_message_types: list[str] = field(default_factory=lambda: [
        "PositionReport",
        "StandardClassBPositionReport",
        "ShipStaticData",
    ])


class AISStreamClient:
    """Async WebSocket client for the aisstream.io live AIS feed.

    Features:
    - Automatic reconnection with exponential backoff and jitter.
    - Configurable bounding-box and message-type subscriptions.
    - Callback-based message dispatch.
    - Graceful shutdown.

    Args:
        api_key: aisstream.io API key.
        on_message: Async callback invoked for each decoded message.
        subscription: Subscription filters (bounding boxes, message types).
    """

    def __init__(
        self,
        api_key: str,
        on_message: Callable[[dict[str, Any]], Awaitable[None]],
        subscription: AISStreamSubscription | None = None,
    ) -> None:
        self._api_key = api_key
        self._on_message = on_message
        self._subscription = subscription or AISStreamSubscription()
        self._ws: ClientConnection | None = None
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._backoff = INITIAL_BACKOFF_SECS

    # ── Public API ─────────────────────────────────────────────────

    async def connect(self) -> None:
        """Start the WebSocket connection in a background task.

        The task runs indefinitely (with auto-reconnect) until
        ``disconnect()`` is called.
        """
        if self._running:
            logger.warning("AISStreamClient is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop(), name="aisstream-client")
        logger.info("AISStreamClient started")

    async def disconnect(self) -> None:
        """Gracefully stop the WebSocket connection."""
        self._running = False

        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("AISStreamClient stopped")

    def subscribe(
        self,
        bounding_boxes: list[list[list[float]]] | None = None,
        filter_message_types: list[str] | None = None,
    ) -> None:
        """Update subscription filters.

        Changes take effect on the next reconnect cycle.

        Args:
            bounding_boxes: New bounding boxes, or ``None`` to keep current.
            filter_message_types: New message type filters, or ``None`` to keep current.
        """
        if bounding_boxes is not None:
            self._subscription.bounding_boxes = bounding_boxes
        if filter_message_types is not None:
            self._subscription.filter_message_types = filter_message_types
        logger.info("Subscription updated: %s", self._subscription)

    @property
    def is_connected(self) -> bool:
        """Whether the WebSocket is currently open."""
        return self._ws is not None and self._ws.close_code is None

    # ── Internal ───────────────────────────────────────────────────

    async def _run_loop(self) -> None:
        """Main reconnection loop with exponential backoff."""
        while self._running:
            try:
                await self._connect_and_listen()
                # Reset backoff on clean disconnect
                self._backoff = INITIAL_BACKOFF_SECS
            except asyncio.CancelledError:
                break
            except Exception:
                if not self._running:
                    break
                logger.exception("AISStream connection error")

                # Exponential backoff with jitter
                jitter = random.uniform(0, JITTER_MAX_SECS)
                delay = min(self._backoff + jitter, MAX_BACKOFF_SECS)
                logger.info("Reconnecting in %.1f seconds...", delay)
                await asyncio.sleep(delay)
                self._backoff = min(self._backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF_SECS)

    async def _connect_and_listen(self) -> None:
        """Establish connection, send subscription, and listen for messages."""
        logger.info("Connecting to aisstream.io...")

        async with websockets.connect(
            AISSTREAM_WS_URL,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=10,
        ) as ws:
            self._ws = ws
            logger.info("Connected to aisstream.io")

            # Send subscription message
            subscribe_msg = {
                "APIKey": self._api_key,
                "BoundingBoxes": self._subscription.bounding_boxes,
                "FilterMessageTypes": self._subscription.filter_message_types,
            }
            await ws.send(json.dumps(subscribe_msg))
            logger.info("Subscription sent: %d bbox(es), types=%s",
                        len(self._subscription.bounding_boxes),
                        self._subscription.filter_message_types)

            # Reset backoff on successful connection
            self._backoff = INITIAL_BACKOFF_SECS

            # Listen for messages
            async for raw_msg in ws:
                if not self._running:
                    break

                try:
                    data = json.loads(raw_msg)
                    await self._on_message(data)
                except json.JSONDecodeError:
                    logger.warning("Received non-JSON message from aisstream.io")
                except Exception:
                    logger.exception("Error processing aisstream message")

        self._ws = None
