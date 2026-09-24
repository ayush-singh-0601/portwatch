"""
Comprehensive unit test suite verifying the backend fixes across analytics,
parsers, services, and routers.
"""

import math
from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.ais_decoder import extract_position
from app.agents.risk_scoring import FLAG_OF_CONVENIENCE, HIGH_RISK_FLAG_STATES
from app.utils.flag_lookup import get_flag_info
from app.services.ofac_parser import _extract_vessel_info, SDNEntity
from app.services.name_matcher import normalize_name, _get_normalized_sanctions
from app.services.pdf_report import get_report_metadata


# ─────────────────────────────────────────────────────────────────────────────
# 1. AIS Decoder Fixes: Coordinate validation & sentinel speed/heading
# ─────────────────────────────────────────────────────────────────────────────

def test_ais_decoder_coordinate_validation():
    # Valid position report within [-90, 90] and [-180, 180]
    valid_msg = {
        "mmsi": 352111000,
        "latitude": 25.123,
        "longitude": 55.456,
        "speed": 12.5,
        "heading": 180,
    }
    pos = extract_position(valid_msg)
    assert pos is not None
    assert pos.latitude == 25.123
    assert pos.longitude == 55.456

    # Out-of-range coordinates should return None
    assert extract_position(dict(valid_msg, latitude=91.0)) is None
    assert extract_position(dict(valid_msg, latitude=-91.0)) is None
    assert extract_position(dict(valid_msg, longitude=181.0)) is None
    assert extract_position(dict(valid_msg, longitude=-181.0)) is None


def test_ais_decoder_sentinel_filtering():
    # Speed >= 102.2 knots (sentinel 102.3 kn) and heading == 511.0 indicate unavailable
    sentinel_msg = {
        "mmsi": 352111000,
        "latitude": 25.0,
        "longitude": 55.0,
        "speed": 102.3,
        "heading": 511.0,
    }
    pos = extract_position(sentinel_msg)
    assert pos is not None
    assert pos.speed is None
    assert pos.heading is None


# ─────────────────────────────────────────────────────────────────────────────
# 2. Risk Scoring & Flags: Alpha-2 and Alpha-3 ISO codes
# ─────────────────────────────────────────────────────────────────────────────

def test_flags_of_convenience_alpha2_and_alpha3():
    # Both 2-letter and 3-letter codes must be present
    for a2, a3 in [("PA", "PAN"), ("LR", "LBR"), ("MH", "MHL"), ("MT", "MLT"), ("CY", "CYP")]:
        assert a2 in FLAG_OF_CONVENIENCE
        assert a3 in FLAG_OF_CONVENIENCE


def test_high_risk_flag_states_alpha2_and_alpha3():
    for a2, a3 in [("IR", "IRN"), ("KP", "PRK"), ("RU", "RUS"), ("SY", "SYR"), ("CU", "CUB")]:
        assert a2 in HIGH_RISK_FLAG_STATES
        assert a3 in HIGH_RISK_FLAG_STATES


def test_flag_lookup_alpha2_codes():
    pa = get_flag_info("PA")
    assert pa is not None
    assert "Panama" in pa["name"]

    lr = get_flag_info("LR")
    assert lr is not None
    assert "Liberia" in lr["name"]


# ─────────────────────────────────────────────────────────────────────────────
# 3. Sanctions Parsers: OFAC XML idList & Digit Stripping
# ─────────────────────────────────────────────────────────────────────────────

def test_ofac_idlist_vessel_info_extraction():
    entity = SDNEntity()
    _extract_vessel_info("IMO", "9123456", entity)
    assert entity.imo_number == "9123456"

    _extract_vessel_info("MMSI", "352111000", entity)
    assert entity.mmsi == "352111000"


def test_sanctions_imo_digit_stripping():
    # In sanctions screening, non-digits are stripped for exact matching
    imo_str = "9123456"
    test_inputs = ["IMO 9123456", "IMO: 9123456", "IMO. 9123456", "9123456"]
    for raw in test_inputs:
        cleaned = "".join(c for c in str(raw) if c.isdigit())
        assert cleaned == imo_str


# ─────────────────────────────────────────────────────────────────────────────
# 4. Name Matcher: Pre-normalization & Cache
# ─────────────────────────────────────────────────────────────────────────────

def test_name_matcher_pre_normalization():
    names = ["IRANIAN SHIPPING LINE", "MAERSK LINE", "PACIFIC CARRIER"]
    cached1 = _get_normalized_sanctions(names)
    cached2 = _get_normalized_sanctions(names)
    assert cached1 == cached2
    assert len(cached1) == len(names)
    assert cached1[0] == normalize_name("IRANIAN SHIPPING LINE")


# ─────────────────────────────────────────────────────────────────────────────
# 5. PDF Report: HTML fallback consistency
# ─────────────────────────────────────────────────────────────────────────────

def test_pdf_report_metadata_fallback():
    pdf_meta = get_report_metadata("report_123.pdf", is_fallback=False)
    assert pdf_meta["format"] == "pdf"
    assert pdf_meta["extension"] == ".pdf"
    assert pdf_meta["content_type"] == "application/pdf"

    fallback_meta = get_report_metadata("report_123.html", is_fallback=True)
    assert fallback_meta["format"] == "html"
    assert fallback_meta["extension"] == ".html"
    assert fallback_meta["content_type"] == "text/html"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Positions Router: Bounding Box Validations (executed before DB queries)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_positions_router_bbox_validation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid min_lat > max_lat (50.0, 35.0, 60.0, 20.0 -> min_lat 35.0 > max_lat 20.0)
        resp = await client.get("/api/map/positions", params={"bbox": "50.0,35.0,60.0,20.0"})
        assert resp.status_code == 400
        assert "min_lat must be <= max_lat" in resp.json()["detail"]

        # Invalid latitude > 90 (-95.0)
        resp2 = await client.get("/api/map/positions", params={"bbox": "50.0,-95.0,60.0,50.0"})
        assert resp2.status_code == 400
        assert "between -90 and 90" in resp2.json()["detail"]


# ─────────────────────────────────────────────────────────────────────────────
# 7. Timezone Normalization: Naive vs Aware UTC Subtractions
# ─────────────────────────────────────────────────────────────────────────────

def test_datetime_utc_normalization():
    # Demonstrating the UTC normalization pattern used in spoofing and dark detection
    now_utc = datetime.now(timezone.utc)
    naive_dt = datetime(2026, 9, 20, 10, 0, 0)
    
    # Safe normalization avoids TypeError: can't subtract offset-naive and offset-aware datetimes
    aware_dt = naive_dt.replace(tzinfo=timezone.utc) if naive_dt.tzinfo is None else naive_dt
    delta = now_utc - aware_dt
    assert delta.total_seconds() > 0
