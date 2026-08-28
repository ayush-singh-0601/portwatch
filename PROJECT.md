# Project: PortWatch Geospatial Proximity Fix

## Architecture
- **Framework**: FastAPI + SQLAlchemy 2.0 (asyncpg) + Alembic
- **Geospatial Processing**: Dual-mode engine
  - Primary (PostGIS): `ST_DWithin` on WGS-84 Geography (`ST_SetSRID(ST_Point(lon, lat), 4326)::geography`)
  - Secondary / Test (Pure Python): `haversine_distance` scan in `backend/app/utils/geo.py`
- **Data Flow**:
  - `DarkVesselDetector` -> `_is_coastal_position` (50 nm / 92.6 km) -> queries `ports` -> classifies dark event threshold (6h vs 24h).
  - `AISAnomalyDetector` -> `_is_near_risk_zone` (30 nm) -> checks `SHIP_BREAKING_YARDS` constants in memory -> queries `ports` for `SANCTIONED_PORT_COUNTRIES` -> triggers loitering risk scoring.
  - `STSTransferDetector` -> `_check_in_port_limits` (5 km) -> queries `ports` -> classifies off-port-limits status.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Port Reference Model | SQLAlchemy 2.0 `Port` model with `unlocode`, `name`, `country`, `latitude`, `longitude` | M1 | ORIGINAL_REQUEST §R1 |
| 2 | Alembic Migration | `003_add_ports_table` migration creating unseeded `ports` reference table | M1 | ORIGINAL_REQUEST §R1 |
| 3 | Model Export | Re-export `Port` in `app/models/__init__.py` for Alembic autogenerate | M1 | ORIGINAL_REQUEST §R4 |
| 4 | Shared Geo Utility | `haversine_distance`, `nm_to_km`, `is_within_nm` in `app/utils/geo.py` | M2 | ORIGINAL_REQUEST §R3 |
| 5 | Ship-Breaking Yards | 5 yard constants (Alang, Gadani, Chattogram, Aliağa, Zhoushan) in `app/utils/geo.py` | M2 | ORIGINAL_REQUEST §R3, §R4 |
| 6 | Spoofing Geo Import | Refactor `spoofing.py` to import `haversine_distance` from `app.utils.geo` | M2 | ORIGINAL_REQUEST §R3 |
| 7 | Coastal Proximity Logic | `_is_coastal_position` (50 nm / 92.6 km) with PostGIS + haversine fallback & empty table warning | M3 | ORIGINAL_REQUEST §R2 |
| 8 | Risk Zone Proximity Logic | `_is_near_risk_zone` (30 nm to yards or sanctioned ports) with fallback & empty table warning | M4 | ORIGINAL_REQUEST §R2 |
| 9 | Port Limits Proximity Logic | `_check_in_port_limits` (5 km to any port) with fallback & empty table warning | M5 | ORIGINAL_REQUEST §R2 |
| 10 | UTF-8 Clean Encoding | Ensure all source and test files decode cleanly as UTF-8 (replace CP-1252 0x97) | M6 | Survey Discovery |
| 11 | Unit & Fallback Tests | Test suites in `tests/test_geo_utils.py` and `tests/test_geo_fallbacks.py` | M6 | ORIGINAL_REQUEST §R4 |
| 12 | Service Docstrings & Comments | Update `DarkVesselDetector`, `STSTransferDetector`, `AISAnomalyDetector` docstrings and remove stale comments | M7 | ORIGINAL_REQUEST §R4 |
| 13 | Commit Hygiene & Atomic Commits | Exactly 12-15 atomic commits, Conventional Commits, <=3 files per commit | M8 | ORIGINAL_REQUEST §R4 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Ports Model & Migration | `app/models/port.py`, `app/models/__init__.py`, `alembic/versions/003_add_ports_table.py` | none | DONE |
| M2 | Shared Geo Utility & Constants | `app/utils/geo.py`, `app/services/spoofing.py` | none | DONE |
| M3 | Coastal Proximity Implementation | `app/services/dark_detection.py` (`_is_coastal_position`) | M1, M2 | DONE |
| M4 | Risk Zone Proximity Implementation | `app/services/spoofing.py` (`_is_near_risk_zone`) | M1, M2 | DONE |
| M5 | Port Limits Proximity Implementation | `app/services/sts_detection.py` (`_check_in_port_limits`) | M1, M2 | DONE |
| M6 | Test Suite & UTF-8 Encoding Fix | Clean CP-1252 byte `0x97`, verify `test_geo_utils.py` and `test_geo_fallbacks.py` | M1-M5 | DONE |
| M7 | Service Docstrings & Cleanup | Clean docstrings in `dark_detection.py`, `spoofing.py`, `sts_detection.py` | M3-M5 | DONE |
| M8 | Final Verification & Commit Hygiene | Run full test suite, verify 12-15 commits, Conventional Commits, audit gate | M1-M7 | DONE |

## Interface Contracts
### `app.utils.geo`
- `haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float`: Returns distance in km. Returns `0.0` for identical coords.
- `nm_to_km(nm: float) -> float`: Multiplies `nm * 1.852`.
- `is_within_nm(lat1, lon1, lat2, lon2, radius_nm: float) -> bool`: Returns `True` if `haversine_distance <= radius_nm * 1.852`.
- `SHIP_BREAKING_YARDS: list[ShipBreakingYard]`: NamedTuples for Alang `(21.41, 72.18)`, Gadani `(25.12, 66.73)`, Chattogram `(22.23, 91.78)`, Aliağa `(38.80, 26.97)`, Zhoushan `(29.99, 122.21)`.

### Detection Services Proximity Contracts
- `DarkVesselDetector._is_coastal_position(lat: float, lon: float) -> bool`: Async. 50 nm / 92.6 km proximity to any port. Fallback on empty table returns `True` with logged warning.
- `AISAnomalyDetector._is_near_risk_zone(lat: float, lon: float) -> bool`: Async. 30 nm proximity to yards (in-memory) or sanctioned ports (`Port.country.in_(SANCTIONED_PORT_COUNTRIES)`). Fallback on empty table returns `False` with logged warning.
- `STSTransferDetector._check_in_port_limits(lat: float, lon: float) -> bool`: Async. 5 km proximity to any port. Fallback on empty table returns `False` with logged warning.

## Code Layout
- `backend/app/models/port.py`: `Port` SQLAlchemy model
- `backend/app/models/__init__.py`: Model registry
- `backend/app/utils/geo.py`: Haversine distance, unit conversion, yard constants
- `backend/app/services/dark_detection.py`: `_is_coastal_position`
- `backend/app/services/spoofing.py`: `_is_near_risk_zone`
- `backend/app/services/sts_detection.py`: `_check_in_port_limits`
- `backend/alembic/versions/003_add_ports_table.py`: Migration for `ports` table
- `backend/tests/test_geo_utils.py`: Unit tests for haversine and yard constants
- `backend/tests/test_geo_fallbacks.py`: Fallback and empty table tests
