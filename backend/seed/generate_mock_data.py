"""
Generate realistic synthetic seed data for the PortWatch platform.

Generates deterministic (seed=42) mock data including:
- 100 vessels across 5 types
- 24 hours of position data along major shipping lanes
- 5 ownership chains
- 10 sanctions entries + 3 matches
- 2 dark events, 1 STS event
- 5 risk scores with factor breakdowns
- 10 port calls

Run::

    python -m seed.generate_mock_data

The script outputs SQL INSERT statements to stdout and can optionally
write them to a file via ``--output`` flag.
"""

from __future__ import annotations

import argparse
import math
import random
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

# ── Deterministic seed ─────────────────────────────────────────────
random.seed(42)

NOW = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

# ── Reference data ─────────────────────────────────────────────────

FLAGS = [
    "PAN", "LBR", "MHL", "HKG", "SGP", "MLT", "BHS", "GRC", "CHN",
    "NOR", "JPN", "GBR", "CYP", "DNK", "DEU", "ITA", "KOR", "USA",
    "TUR", "IND", "ARE", "SAU", "NGA", "VNM", "IDN", "MYS", "THA",
    "BRA", "RUS", "IRN", "PRK", "SYR", "VEN", "CMR", "TGO", "TZA",
]

VESSEL_TYPES = {
    "cargo": 40,
    "tanker": 25,
    "fishing": 15,
    "passenger": 10,
    "other": 10,
}

CARGO_NAME_PREFIXES = [
    "Star", "Ocean", "Sea", "Pacific", "Atlantic", "Global", "Orient",
    "Eagle", "Diamond", "Golden", "Silver", "Crystal", "Royal", "Crown",
    "Nordic", "Maersk", "Evergreen", "Cosco", "Yang Ming", "Hanjin",
]
CARGO_NAME_SUFFIXES = [
    "Express", "Voyager", "Pioneer", "Navigator", "Carrier", "Spirit",
    "Fortune", "Harmony", "Victory", "Progress", "Horizon", "Trader",
    "Merchant", "Glory", "Star", "Bridge", "Wave", "Wind", "Dream", "Pride",
]

TANKER_NAME_PREFIXES = [
    "Crude", "Gulf", "Petro", "Arabian", "Caspian", "Nordic", "Baltic",
    "Olympic", "Titan", "Atlas", "Neptune", "Poseidon", "Meridian",
]
TANKER_NAME_SUFFIXES = [
    "Strength", "Power", "Energy", "Spirit", "Venture", "Promise",
    "Legacy", "Trust", "Resolve", "Valor",
]

FISHING_NAMES = [
    "Hai Feng", "Dong Yuan", "Fu Yuan Yu", "Lian Run", "Zhong Yuan",
    "Oyang 75", "Hua Li 8", "Lu Rong Yu", "Jin Sheng", "Tian Yu",
    "Yong Xing", "Da Yang", "Kai Xin", "Shun Li", "Ping An",
]

PASSENGER_NAMES = [
    "Coral Princess", "Azure Seas", "Sapphire Dream", "Island Explorer",
    "Coastal Star", "Harbour Queen", "Bay Cruiser", "Sunset Voyager",
    "Pearl Melody", "Emerald Wave",
]

OTHER_NAMES = [
    "Offshore Valiant", "Deep Explorer", "Cable Pioneer", "Survey Master",
    "Anchor Handler II", "Tug Resolute", "Barge Atlas", "Dredger King",
    "Research Horizon", "Supply Champion",
]

# ── Major shipping lanes (waypoints as lat/lon pairs) ──────────────
SHIPPING_LANES = {
    "strait_of_malacca": [
        (5.8, 95.3), (4.2, 99.8), (2.5, 101.5), (1.3, 103.8),
    ],
    "english_channel": [
        (48.5, -5.5), (49.5, -3.0), (50.5, -0.5), (51.0, 1.5),
    ],
    "suez_approach": [
        (30.0, 32.5), (29.9, 32.56), (29.8, 32.58), (29.7, 32.6),
    ],
    "gulf_of_aden": [
        (12.0, 45.0), (12.5, 47.0), (13.0, 49.0), (12.8, 51.0),
    ],
    "singapore_strait": [
        (1.1, 103.5), (1.2, 103.8), (1.25, 104.1), (1.3, 104.4),
    ],
}

PORTS = [
    ("Singapore", "SGP", "SGSIN"),
    ("Rotterdam", "NLD", "NLRTM"),
    ("Shanghai", "CHN", "CNSHA"),
    ("Fujairah", "ARE", "AEFJR"),
    ("Busan", "KOR", "KRPUS"),
    ("Port Said", "EGY", "EGPSD"),
    ("Piraeus", "GRC", "GRPIR"),
    ("Houston", "USA", "USHOU"),
    ("Jeddah", "SAU", "SAJED"),
    ("Mumbai", "IND", "INBOM"),
]

COMPANY_NAMES = [
    "Oceanic Maritime Holdings Ltd", "Straits Shipping Pte Ltd",
    "Pan-Asia Maritime Corp", "Golden Anchor Investments SA",
    "Adriatic Ship Management GmbH", "Blue Horizon Tankers LLC",
    "Meridian Bulk Carriers Inc", "Caspian Energy Transport JSC",
    "Neptunian Holdings BVI", "Seahawk Maritime Partners",
    "Velvet Shipping SA", "Iron Gate Maritime Ltd",
    "Crescent Moon Logistics FZE", "Tiger Bay Investments LP",
    "Silverstream Maritime Co", "Eastern Compass Shipping Ltd",
    "Nordic Wave Management AS", "Coral Reef Enterprises Inc",
    "Trident Ocean Services BV", "Aegean Star Marine Corp",
]

ENTITY_TYPES = ["company", "company", "company", "person", "trust"]

COUNTRIES = ["PAN", "LBR", "MHL", "HKG", "SGP", "GBR", "GRC", "CYP", "ARE", "BVI"]

RELATIONSHIP_TYPES = ["owner", "operator", "manager", "beneficial_owner", "charterer"]

SANCTIONS_PROGRAMS = [
    "IRAN", "SYRIA", "DPRK", "UKRAINE-EO13662", "SDGT",
    "CUBA", "VENEZUELA", "CYBER2", "IFSR", "SDNTK",
]


# ── Vessel generation ─────────────────────────────────────────────

def _generate_vessel_name(vtype: str, idx: int) -> str:
    """Generate a realistic vessel name based on type."""
    if vtype == "cargo":
        prefix = random.choice(CARGO_NAME_PREFIXES)
        suffix = random.choice(CARGO_NAME_SUFFIXES)
        return f"{prefix} {suffix}"
    elif vtype == "tanker":
        prefix = random.choice(TANKER_NAME_PREFIXES)
        suffix = random.choice(TANKER_NAME_SUFFIXES)
        return f"{prefix} {suffix}"
    elif vtype == "fishing":
        return random.choice(FISHING_NAMES) + (f" {idx}" if idx > len(FISHING_NAMES) else "")
    elif vtype == "passenger":
        return random.choice(PASSENGER_NAMES)
    else:
        return random.choice(OTHER_NAMES)


def _generate_call_sign() -> str:
    """Generate a realistic radio call sign."""
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return "".join(random.choices(letters, k=random.randint(4, 6)))


def generate_vessels() -> list[dict[str, Any]]:
    """Generate 100 vessels with realistic attributes."""
    vessels: list[dict[str, Any]] = []
    used_names: set[str] = set()
    imo_base = 9100000
    mmsi_base = 200000000

    idx = 0
    for vtype, count in VESSEL_TYPES.items():
        for i in range(count):
            # Ensure unique names
            for _ in range(20):
                name = _generate_vessel_name(vtype, i)
                if name not in used_names:
                    break
            else:
                name = f"{name} {idx}"
            used_names.add(name)

            vessel = {
                "imo": imo_base + idx,
                "mmsi": mmsi_base + idx * 111,
                "name": name,
                "flag": random.choice(FLAGS),
                "vessel_type": vtype,
                "gross_tonnage": random.randint(
                    {"cargo": 5000, "tanker": 8000, "fishing": 200, "passenger": 20000, "other": 500}[vtype],
                    {"cargo": 120000, "tanker": 200000, "fishing": 3000, "passenger": 150000, "other": 15000}[vtype],
                ),
                "dwt": random.randint(3000, 300000) if vtype in ("cargo", "tanker") else None,
                "year_built": random.randint(1995, 2024),
                "call_sign": _generate_call_sign(),
                "created_at": (NOW - timedelta(days=random.randint(30, 365))).isoformat(),
                "updated_at": NOW.isoformat(),
            }
            vessels.append(vessel)
            idx += 1

    return vessels


# ── Position generation (along shipping lanes) ────────────────────

def _interpolate_lane(lane: list[tuple[float, float]], t: float) -> tuple[float, float]:
    """Interpolate a position along a shipping lane at fraction t (0-1)."""
    n = len(lane) - 1
    segment = min(int(t * n), n - 1)
    local_t = (t * n) - segment
    lat = lane[segment][0] + (lane[segment + 1][0] - lane[segment][0]) * local_t
    lon = lane[segment][1] + (lane[segment + 1][1] - lane[segment][1]) * local_t
    # Add slight random drift
    lat += random.gauss(0, 0.01)
    lon += random.gauss(0, 0.01)
    return round(lat, 6), round(lon, 6)


def _bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate bearing between two points in degrees."""
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    return (math.degrees(math.atan2(dlon, dlat)) + 360) % 360


def generate_positions(vessels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Generate 24 hours of position data for all vessels.

    Each vessel is assigned to a random shipping lane and progresses
    along it over 24 hours at its assigned speed.
    """
    positions: list[dict[str, Any]] = []
    lane_names = list(SHIPPING_LANES.keys())

    for vessel in vessels:
        lane_name = random.choice(lane_names)
        lane = SHIPPING_LANES[lane_name]
        speed = random.uniform(8.0, 18.0)  # knots

        # Generate positions every 10 minutes for 24 hours
        num_points = 144  # 24h * 6 per hour
        start_t = random.uniform(0.0, 0.3)  # Start at a random point on the lane
        t_increment = 0.7 / num_points  # Traverse ~70% of the lane

        prev_lat, prev_lon = None, None

        for i in range(num_points):
            t = min(start_t + i * t_increment, 0.999)
            lat, lon = _interpolate_lane(lane, t)
            time = NOW - timedelta(hours=24) + timedelta(minutes=i * 10)

            # Calculate course from previous point
            course = 0.0
            if prev_lat is not None:
                course = _bearing(prev_lat, prev_lon, lat, lon)

            positions.append({
                "time": time.isoformat(),
                "mmsi": vessel["mmsi"],
                "latitude": lat,
                "longitude": lon,
                "speed": round(speed + random.gauss(0, 0.5), 1),
                "course": round(course, 1),
                "heading": round((course + random.gauss(0, 3)) % 360, 1),
                "nav_status": 0,  # Under way using engine
                "msg_type": random.choice([1, 2, 3, 18]),
            })

            prev_lat, prev_lon = lat, lon

    return positions


# ── Ownership chains ──────────────────────────────────────────────

def generate_ownership(vessels: list[dict[str, Any]]) -> tuple[list[dict], list[dict]]:
    """Generate 5 ownership chains of 3-5 entities each."""
    entities: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    entity_id = 1

    for chain_idx in range(5):
        vessel = vessels[chain_idx]
        chain_length = random.randint(3, 5)
        chain_entity_ids: list[int] = []

        for depth in range(chain_length):
            name = COMPANY_NAMES[(chain_idx * 5 + depth) % len(COMPANY_NAMES)]
            etype = ENTITY_TYPES[depth % len(ENTITY_TYPES)]
            country = COUNTRIES[(chain_idx + depth) % len(COUNTRIES)]

            entities.append({
                "id": entity_id,
                "name": name,
                "entity_type": etype,
                "country": country,
                "registration": f"REG-{country}-{random.randint(100000, 999999)}",
                "created_at": (NOW - timedelta(days=random.randint(365, 3650))).isoformat(),
            })
            chain_entity_ids.append(entity_id)
            entity_id += 1

        # Create edges: each entity owns the next one in the chain
        for depth in range(len(chain_entity_ids) - 1):
            rel_type = RELATIONSHIP_TYPES[depth % len(RELATIONSHIP_TYPES)]
            edges.append({
                "id": len(edges) + 1,
                "source_entity_id": chain_entity_ids[depth + 1],
                "target_entity_id": chain_entity_ids[depth],
                "relationship_type": rel_type,
                "vessel_imo": vessel["imo"],
                "effective_date": (NOW - timedelta(days=random.randint(365, 1825))).strftime("%Y-%m-%d"),
                "end_date": None,
            })

    return entities, edges


# ── Sanctions entries + matches ────────────────────────────────────

def generate_sanctions(vessels: list[dict[str, Any]]) -> tuple[list[dict], list[dict]]:
    """Generate 10 sanctions entries and 3 matches (exact + fuzzy)."""
    entries: list[dict[str, Any]] = []

    sanctions_data = [
        ("OFAC", "JADE STAR TANKERS", "vessel", "IRAN"),
        ("OFAC", "SAPPHIRE MARITIME LTD", "organization", "SDGT"),
        ("EU", "CRIMSON SHIPPING COMPANY", "organization", "SYRIA"),
        ("EU", "AL-QUDS PETROLEUM", "organization", "IRAN"),
        ("UN", "CHONGCHONGANG SHIPPING", "organization", "DPRK"),
        ("OFSI", "MERIDIAN OFFSHORE SERVICES", "organization", "RUSSIA"),
        ("OFAC", "PETROCHEMICAL COMMERCIAL COMPANY", "organization", "IRAN"),
        ("EU", "VELVET MARITIME ENTERPRISES", "vessel", "UKRAINE-EO13662"),
        ("UN", "PAEKMA SHIPPING CO", "organization", "DPRK"),
        ("OFAC", "GOLDEN ANCHOR INVESTMENTS", "organization", "SDGT"),
    ]

    for i, (source, name, etype, program) in enumerate(sanctions_data, 1):
        entries.append({
            "id": i,
            "source": source,
            "entity_name": name,
            "entity_type": etype,
            "program": program,
            "list_id": f"{source}-{random.randint(10000, 99999)}",
            "aliases": [f"{name} ALIAS"] if random.random() > 0.5 else None,
            "imo_number": str(vessels[i - 1]["imo"]) if i <= 3 else None,
            "last_updated": NOW.isoformat(),
        })

    # Sanctions matches
    matches: list[dict[str, Any]] = [
        {
            "id": 1,
            "vessel_imo": vessels[0]["imo"],
            "matched_entity_id": None,
            "sanctions_entry_id": 1,
            "match_score": 100.0,
            "match_type": "exact",
            "matched_field": "imo_number",
            "created_at": NOW.isoformat(),
        },
        {
            "id": 2,
            "vessel_imo": vessels[1]["imo"],
            "matched_entity_id": None,
            "sanctions_entry_id": 2,
            "match_score": 92.5,
            "match_type": "fuzzy",
            "matched_field": "vessel_name",
            "created_at": NOW.isoformat(),
        },
        {
            "id": 3,
            "vessel_imo": vessels[4]["imo"],
            "matched_entity_id": 1,  # Linked to an ownership entity
            "sanctions_entry_id": 10,
            "match_score": 88.3,
            "match_type": "fuzzy",
            "matched_field": "owner_name",
            "created_at": NOW.isoformat(),
        },
    ]

    return entries, matches


# ── Dark events ────────────────────────────────────────────────────

def generate_dark_events(vessels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Generate 2 dark (AIS-off) events."""
    return [
        {
            "id": 1,
            "vessel_imo": vessels[3]["imo"],
            "start_time": (NOW - timedelta(hours=18)).isoformat(),
            "start_lat": 12.5,
            "start_lon": 47.5,
            "end_time": (NOW - timedelta(hours=6)).isoformat(),
            "end_lat": 13.2,
            "end_lon": 49.1,
            "duration_hours": 12.0,
            "zone_type": "open_ocean",
            "created_at": NOW.isoformat(),
        },
        {
            "id": 2,
            "vessel_imo": vessels[7]["imo"],
            "start_time": (NOW - timedelta(hours=8)).isoformat(),
            "start_lat": 1.15,
            "start_lon": 103.7,
            "end_time": None,
            "end_lat": None,
            "end_lon": None,
            "duration_hours": 8.0,
            "zone_type": "coastal",
            "created_at": NOW.isoformat(),
        },
    ]


# ── STS event ─────────────────────────────────────────────────────

def generate_sts_events(vessels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Generate 1 Ship-to-Ship transfer event."""
    return [
        {
            "id": 1,
            "vessel_a_imo": vessels[1]["imo"],
            "vessel_b_imo": vessels[5]["imo"],
            "start_time": (NOW - timedelta(hours=14)).isoformat(),
            "end_time": (NOW - timedelta(hours=10)).isoformat(),
            "latitude": 25.5,
            "longitude": 56.8,
            "min_distance_m": 45.0,
            "duration_minutes": 240.0,
            "in_port_limits": False,
            "created_at": NOW.isoformat(),
        },
    ]


# ── Risk scores ────────────────────────────────────────────────────

def generate_risk_scores(vessels: list[dict[str, Any]]) -> tuple[list[dict], list[dict]]:
    """Generate 5 risk scores with factor breakdowns."""
    scores: list[dict[str, Any]] = []
    factors: list[dict[str, Any]] = []
    factor_id = 1

    risk_data = [
        (0, 78, [
            ("sanctions_match", 35, "IMO number matches OFAC SDN entry"),
            ("dark_activity", 18, "1 dark event (12h) in Gulf of Aden"),
            ("flag_risk", 15, "Flagged to high-risk state"),
            ("sts_transfer", 10, "1 open-ocean STS transfer detected"),
        ]),
        (1, 62, [
            ("sanctions_match", 28, "Fuzzy match (92.5%) to OFAC entity"),
            ("sts_transfer", 20, "STS transfer in open ocean — Fujairah anchorage"),
            ("flag_risk", 14, "Flag state on Paris MoU grey list"),
        ]),
        (3, 45, [
            ("dark_activity", 25, "12-hour AIS gap in open ocean"),
            ("flag_risk", 15, "Flagged to Cameroon (Paris MoU black list)"),
            ("psc_history", 5, "1 PSC detention in past 12 months"),
        ]),
        (4, 33, [
            ("sanctions_match", 18, "Owner entity fuzzy match (88.3%) to OFAC"),
            ("flag_risk", 15, "High-risk flag registry"),
        ]),
        (9, 12, [
            ("psc_history", 7, "2 PSC deficiencies in past 12 months"),
            ("flag_risk", 5, "Minor flag risk"),
        ]),
    ]

    for score_id, (vessel_idx, total, factor_list) in enumerate(risk_data, 1):
        scores.append({
            "id": score_id,
            "vessel_imo": vessels[vessel_idx]["imo"],
            "total_score": total,
            "calculated_at": NOW.isoformat(),
        })

        for factor_name, points, description in factor_list:
            factors.append({
                "id": factor_id,
                "risk_score_id": score_id,
                "factor_name": factor_name,
                "points": points,
                "evidence_description": description,
                "evidence_link": None,
            })
            factor_id += 1

    return scores, factors


# ── Port calls ─────────────────────────────────────────────────────

def generate_port_calls(vessels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Generate 10 port calls across different vessels."""
    port_calls: list[dict[str, Any]] = []

    for i in range(10):
        port_name, port_country, unlocode = PORTS[i]
        vessel_idx = i % len(vessels)
        arrival = NOW - timedelta(days=random.randint(1, 30), hours=random.randint(0, 23))
        departure = arrival + timedelta(hours=random.randint(12, 96)) if random.random() > 0.2 else None

        port_calls.append({
            "id": i + 1,
            "vessel_imo": vessels[vessel_idx]["imo"],
            "port_name": port_name,
            "port_country": port_country,
            "unlocode": unlocode,
            "arrival_time": arrival.isoformat(),
            "departure_time": departure.isoformat() if departure else None,
            "psc_detention": i == 5,  # One detention
            "psc_deficiencies": random.choice([0, 0, 0, 1, 2, 3]) if i != 5 else 5,
            "created_at": arrival.isoformat(),
        })

    return port_calls


# ── SQL output ─────────────────────────────────────────────────────

def _sql_val(v: Any) -> str:
    """Format a Python value as a SQL literal."""
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, int | float):
        return str(v)
    if isinstance(v, list):
        inner = ", ".join(f"'{str(item)}'" for item in v)
        return f"ARRAY[{inner}]"
    # String — escape single quotes
    return f"'{str(v).replace(chr(39), chr(39)+chr(39))}'"


def _generate_insert(table: str, rows: list[dict[str, Any]]) -> str:
    """Generate a SQL INSERT statement for a list of row dicts."""
    if not rows:
        return ""
    columns = list(rows[0].keys())
    col_str = ", ".join(columns)
    value_rows: list[str] = []
    for row in rows:
        vals = ", ".join(_sql_val(row[c]) for c in columns)
        value_rows.append(f"  ({vals})")
    values_str = ",\n".join(value_rows)
    return f"INSERT INTO {table} ({col_str}) VALUES\n{values_str}\nON CONFLICT DO NOTHING;\n"


def generate_all_sql() -> str:
    """Generate all seed data as SQL INSERT statements.

    Returns:
        Complete SQL script as a string.
    """
    vessels = generate_vessels()
    positions = generate_positions(vessels)
    entities, ownership_edges = generate_ownership(vessels)
    sanctions_entries, sanctions_matches = generate_sanctions(vessels)
    dark_events = generate_dark_events(vessels)
    sts_events = generate_sts_events(vessels)
    risk_scores, risk_factors = generate_risk_scores(vessels)
    port_calls = generate_port_calls(vessels)

    parts = [
        "-- ============================================================",
        "-- PortWatch Seed Data (deterministic, seed=42)",
        f"-- Generated: {NOW.isoformat()}",
        "-- ============================================================",
        "",
        "BEGIN;",
        "",
        f"-- {len(vessels)} vessels",
        _generate_insert("vessels", vessels),
        f"-- {len(positions)} position reports (24h)",
        _generate_insert("vessel_positions", positions),
        f"-- {len(entities)} ownership entities",
        _generate_insert("ownership_entities", entities),
        f"-- {len(ownership_edges)} ownership edges",
        _generate_insert("ownership_edges", ownership_edges),
        f"-- {len(sanctions_entries)} sanctions entries",
        _generate_insert("sanctions_entries", sanctions_entries),
        f"-- {len(sanctions_matches)} sanctions matches",
        _generate_insert("sanctions_matches", sanctions_matches),
        f"-- {len(dark_events)} dark events",
        _generate_insert("dark_events", dark_events),
        f"-- {len(sts_events)} STS events",
        _generate_insert("sts_events", sts_events),
        f"-- {len(risk_scores)} risk scores",
        _generate_insert("risk_scores", risk_scores),
        f"-- {len(risk_factors)} risk factors",
        _generate_insert("risk_factors", risk_factors),
        f"-- {len(port_calls)} port calls",
        _generate_insert("port_calls", port_calls),
        "",
        "COMMIT;",
        "",
        "-- ============================================================",
        f"-- Summary: {len(vessels)} vessels, {len(positions)} positions,",
        f"--   {len(entities)} entities, {len(ownership_edges)} edges,",
        f"--   {len(sanctions_entries)} sanctions entries, {len(sanctions_matches)} matches,",
        f"--   {len(dark_events)} dark events, {len(sts_events)} STS events,",
        f"--   {len(risk_scores)} risk scores, {len(port_calls)} port calls",
        "-- ============================================================",
    ]

    return "\n".join(parts)


def main() -> None:
    """CLI entry point: generate seed SQL and print or write to file."""
    parser = argparse.ArgumentParser(description="Generate PortWatch seed data")
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print only the summary statistics",
    )
    args = parser.parse_args()

    if args.summary:
        vessels = generate_vessels()
        positions = generate_positions(vessels)
        entities, edges = generate_ownership(vessels)
        sanctions_entries, sanctions_matches = generate_sanctions(vessels)
        dark = generate_dark_events(vessels)
        sts = generate_sts_events(vessels)
        scores, factors = generate_risk_scores(vessels)
        ports = generate_port_calls(vessels)

        print("PortWatch Seed Data Summary:")
        print(f"  Vessels:           {len(vessels)}")
        print(f"  Positions:         {len(positions)}")
        print(f"  Ownership Entities:{len(entities)}")
        print(f"  Ownership Edges:   {len(edges)}")
        print(f"  Sanctions Entries: {len(sanctions_entries)}")
        print(f"  Sanctions Matches: {len(sanctions_matches)}")
        print(f"  Dark Events:       {len(dark)}")
        print(f"  STS Events:        {len(sts)}")
        print(f"  Risk Scores:       {len(scores)}")
        print(f"  Risk Factors:      {len(factors)}")
        print(f"  Port Calls:        {len(ports)}")
        return

    sql = generate_all_sql()

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(sql)
        print(f"Seed data written to {args.output}", file=sys.stderr)
    else:
        print(sql)


if __name__ == "__main__":
    main()
