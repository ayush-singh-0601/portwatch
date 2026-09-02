"""
Unit tests for ais_decoder module.
"""

import pytest
from app.services.ais_decoder import (
    decode_aisstream_message,
    decode_nmea,
    extract_position,
    extract_vessel_identity,
)


def test_extract_position_valid():
    data = {
        "mmsi": 355123456,
        "latitude": 1.35,
        "longitude": 103.82,
        "speed": 12.5,
        "course": 180.0,
        "heading": 178.0,
    }
    pos = extract_position(data)
    assert pos is not None
    assert pos.mmsi == 355123456
    assert pos.latitude == 1.35
    assert pos.longitude == 103.82
    assert pos.speed == 12.5


def test_extract_position_out_of_bounds_lat_lon():
    # Lat > 90
    pos1 = extract_position({"mmsi": 123456789, "latitude": 95.0, "longitude": 10.0})
    assert pos1 is None

    # Lon > 180
    pos2 = extract_position({"mmsi": 123456789, "latitude": 45.0, "longitude": 185.0})
    assert pos2 is None

    # AIS default 91.0 / 181.0
    pos3 = extract_position({"mmsi": 123456789, "latitude": 91.0, "longitude": 181.0})
    assert pos3 is None


def test_extract_vessel_identity_valid():
    data = {
        "mmsi": 355123456,
        "name": "PACIFIC EXPLORER",
        "imo": 9812345,
        "call_sign": "3EAB2",
        "ship_type": 70,
    }
    identity = extract_vessel_identity(data)
    assert identity is not None
    assert identity.mmsi == 355123456
    assert identity.name == "PACIFIC EXPLORER"
    assert identity.imo == 9812345


def test_decode_aisstream_message_position_report():
    msg = {
        "MessageType": "PositionReport",
        "MetaData": {"MMSI": 244123456, "ShipName": "DUTCH TRADER"},
        "Message": {
            "PositionReport": {
                "Latitude": 52.1,
                "Longitude": 4.3,
                "Sog": 8.2,
                "Cog": 90.0,
                "TrueHeading": 88,
            }
        },
    }
    decoded = decode_aisstream_message(msg)
    assert decoded["mmsi"] == 244123456
    assert decoded["latitude"] == 52.1
    assert decoded["longitude"] == 4.3
    assert decoded["speed"] == 8.2
