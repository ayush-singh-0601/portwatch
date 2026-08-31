"""
AIS message decoder — wrapper around pyais v3.

Provides helpers to decode raw NMEA sentences, aisstream.io JSON
messages, and extract structured position / vessel-identity data.

Usage::

    from app.services.ais_decoder import decode_nmea, extract_position

    decoded = decode_nmea("!AIVDM,1,1,,B,15MgK70P00G?Ufh@0H7H800008vP,0*4E")
    pos = extract_position(decoded)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from pyais import decode as pyais_decode
from pyais.messages import NMEAMessage

logger = logging.getLogger(__name__)

import time

# Multi-part message buffer keyed by buffer_key -> (timestamp, [fragments])
_fragment_buffer: dict[str, tuple[float, list[NMEAMessage]]] = {}
_MAX_BUFFER_SIZE = 1000
_FRAGMENT_TTL_SECS = 60.0


def _prune_fragment_buffer(now: float) -> None:
    """Prune expired fragments and enforce max buffer size."""
    expired_keys = [
        k for k, (ts, _) in _fragment_buffer.items()
        if now - ts > _FRAGMENT_TTL_SECS
    ]
    for k in expired_keys:
        _fragment_buffer.pop(k, None)

    # If still over capacity, evict oldest entries
    if len(_fragment_buffer) > _MAX_BUFFER_SIZE:
        sorted_keys = sorted(_fragment_buffer.keys(), key=lambda k: _fragment_buffer[k][0])
        for k in sorted_keys[: len(_fragment_buffer) - _MAX_BUFFER_SIZE]:
            _fragment_buffer.pop(k, None)


@dataclass
class PositionData:
    """Extracted position fields from a decoded AIS message."""

    mmsi: int
    latitude: float
    longitude: float
    speed: float | None = None
    course: float | None = None
    heading: float | None = None
    nav_status: int | None = None
    msg_type: int | None = None
    timestamp: str | None = None


@dataclass
class VesselIdentity:
    """Static vessel data extracted from AIS message types 5 / 24."""

    mmsi: int
    imo: int | None = None
    name: str | None = None
    call_sign: str | None = None
    ship_type: int | None = None
    destination: str | None = None
    draught: float | None = None
    eta: str | None = None


def decode_nmea(raw: str) -> dict[str, Any]:
    """Decode a single NMEA sentence (or multi-part group) via pyais.

    Handles multi-part message assembly automatically.  Fragments are
    buffered until all parts arrive, at which point the complete
    message is decoded.

    Args:
        raw: Raw NMEA sentence string, e.g.
            ``"!AIVDM,1,1,,B,15MgK70P00G?Ufh@0H7H800008vP,0*4E"``

    Returns:
        Decoded message as a dictionary, or an empty dict if the
        message is incomplete (still waiting for fragments).
    """
    try:
        nmea = NMEAMessage(raw.encode())
    except Exception:
        logger.warning("Failed to parse NMEA sentence: %s", raw[:80])
        return {}

    # Single-part message
    if nmea.frag_cnt == 1:
        try:
            decoded = nmea.decode()
            return decoded.asdict()
        except Exception:
            logger.warning("Failed to decode single-part NMEA: %s", raw[:80])
            return {}

    # Multi-part message — buffer fragments with timestamp
    now = time.time()
    _prune_fragment_buffer(now)
    buffer_key = f"{nmea.frag_cnt}_{nmea.seq_id}"

    if nmea.frag_num == 1:
        _fragment_buffer[buffer_key] = (now, [nmea])
    else:
        if buffer_key not in _fragment_buffer:
            logger.debug("Received fragment %d without fragment 1, discarding", nmea.frag_num)
            return {}
        _fragment_buffer[buffer_key][1].append(nmea)

    # Check if all fragments have arrived
    if len(_fragment_buffer[buffer_key][1]) == nmea.frag_cnt:
        _, fragments = _fragment_buffer.pop(buffer_key)
        try:
            decoded = fragments[0].decode(*fragments[1:])
            return decoded.asdict()
        except Exception:
            logger.warning("Failed to decode multi-part NMEA (key=%s)", buffer_key)
            return {}

    return {}


def decode_aisstream_message(data: dict[str, Any]) -> dict[str, Any]:
    """Decode an aisstream.io JSON message into a normalized dict.

    aisstream.io messages have the structure::

        {
            "MessageType": "PositionReport",
            "MetaData": {...},
            "Message": {
                "PositionReport": {...}
            }
        }

    Args:
        data: Raw JSON message from aisstream.io WebSocket.

    Returns:
        Normalized dictionary with AIS fields.
    """
    result: dict[str, Any] = {}

    metadata = data.get("MetaData", {})
    result["mmsi"] = metadata.get("MMSI")
    result["time_utc"] = metadata.get("time_utc")
    result["ship_name"] = metadata.get("ShipName", "").strip()

    msg_type = data.get("MessageType", "")
    message_content = data.get("Message", {})

    # Extract the inner message based on type
    inner = message_content.get(msg_type, {})

    if msg_type in ("PositionReport", "StandardClassBPositionReport", "ExtendedClassBPositionReport"):
        result["msg_type_str"] = msg_type
        result["latitude"] = inner.get("Latitude")
        result["longitude"] = inner.get("Longitude")
        result["speed"] = inner.get("Sog")
        result["course"] = inner.get("Cog")
        result["heading"] = inner.get("TrueHeading")
        result["nav_status"] = inner.get("NavigationalStatus")
        result["msg_type"] = inner.get("MessageID")

    elif msg_type == "ShipStaticData":
        result["msg_type_str"] = msg_type
        result["imo"] = inner.get("ImoNumber")
        result["call_sign"] = inner.get("CallSign", "").strip()
        result["ship_type"] = inner.get("Type")
        result["destination"] = inner.get("Destination", "").strip()
        result["name"] = inner.get("Name", "").strip()
        dim = inner.get("Dimension", {})
        result["dimension"] = dim

    return result


def extract_position(decoded: dict[str, Any]) -> PositionData | None:
    """Extract a ``PositionData`` from a decoded AIS message.

    Returns ``None`` if the message does not contain valid position data.

    Args:
        decoded: Dictionary from ``decode_nmea`` or ``decode_aisstream_message``.

    Returns:
        A ``PositionData`` instance or ``None``.
    """
    mmsi = decoded.get("mmsi")
    lat = decoded.get("latitude") or decoded.get("lat")
    lon = decoded.get("longitude") or decoded.get("lon")

    if mmsi is None or lat is None or lon is None:
        return None

    # Discard invalid coordinates (AIS default for "not available")
    if lat == 91.0 or lon == 181.0:
        return None

    return PositionData(
        mmsi=int(mmsi),
        latitude=float(lat),
        longitude=float(lon),
        speed=_safe_float(decoded.get("speed") or decoded.get("sog")),
        course=_safe_float(decoded.get("course") or decoded.get("cog")),
        heading=_safe_float(decoded.get("heading") or decoded.get("true_heading")),
        nav_status=_safe_int(decoded.get("nav_status") or decoded.get("status")),
        msg_type=_safe_int(decoded.get("msg_type")),
        timestamp=decoded.get("time_utc"),
    )


def extract_vessel_identity(decoded: dict[str, Any]) -> VesselIdentity | None:
    """Extract static vessel identity from a decoded AIS message (type 5/24).

    Returns ``None`` if the message does not contain vessel identity data.

    Args:
        decoded: Dictionary from ``decode_nmea`` or ``decode_aisstream_message``.

    Returns:
        A ``VesselIdentity`` instance or ``None``.
    """
    mmsi = decoded.get("mmsi")
    if mmsi is None:
        return None

    name = decoded.get("name") or decoded.get("shipname") or decoded.get("ship_name")
    imo = decoded.get("imo")

    # Only return if we have at least a name or IMO
    if not name and not imo:
        return None

    return VesselIdentity(
        mmsi=int(mmsi),
        imo=_safe_int(imo),
        name=name.strip() if isinstance(name, str) else None,
        call_sign=(decoded.get("call_sign") or decoded.get("callsign") or "").strip() or None,
        ship_type=_safe_int(decoded.get("ship_type")),
        destination=(decoded.get("destination") or "").strip() or None,
        draught=_safe_float(decoded.get("draught")),
        eta=decoded.get("eta"),
    )


def _safe_float(value: Any) -> float | None:
    """Safely convert a value to float, returning None on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _safe_int(value: Any) -> int | None:
    """Safely convert a value to int, returning None on failure."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None
