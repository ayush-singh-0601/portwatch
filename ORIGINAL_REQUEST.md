# Original User Request

## 2026-08-19T14:59:39Z

Fix the three stubbed geospatial proximity methods in the PortWatch backend that
always return hardcoded `True`/`False`, making dark-vessel detection thresholds
wrong, loitering detection permanently dead, and STS off-port filtering broken.
The fix requires a `ports` reference table with real coordinates, PostGIS
proximity queries, and re-wiring those queries back into all three detection
services, delivered as 12–15 atomic, reviewable git commits.

Working directory: C:\Users\KIIT0001\desktop\portwatch
Integrity mode: development

---

## Background

Three methods in the backend always return a hardcoded constant instead of doing
real geospatial work:

| File | Method | Hardcoded return | Impact |
|---|---|---|---|
| `backend/app/services/dark_detection.py` | `_is_coastal_position` | `True` | Every dark event is classified "coastal" (6 h threshold), never "open ocean" (24 h) |
| `backend/app/services/spoofing.py` | `_is_near_risk_zone` | `False` | Loitering detection produces zero results regardless of vessel behaviour |
| `backend/app/services/sts_detection.py` | `_check_in_port_limits` | `False` | Every STS event is reported as "off-port-limits", even those inside a port |

The root cause (documented in the comments) is that the `port_calls` table has
no coordinate columns. A proper geofence/ports reference table with lat/lon
(or PostGIS geometry) is needed.

## Requirements

### R1. Ports reference table and migration
Add an Alembic migration that creates a `ports` table with at minimum: `unlocode`
(PK or unique), `name`, `country`, `latitude`, `longitude`, and optionally a
PostGIS geography column for spatial indexing. Do NOT add any seed data —
the table starts empty and the proximity methods must handle this gracefully.

### R2. Implement real geospatial proximity logic
Replace all three stubbed methods with real implementations that query the new
`ports` table:

- `_is_coastal_position(lat, lon)` — return `True` if within 50 nautical miles
  (≈ 92.6 km) of any port in the `ports` table. Use PostGIS `ST_DWithin` on
  geography if available; fall back to haversine distance computed in Python if
  the `ports` table is empty or PostGIS is absent.
- `_is_near_risk_zone(lat, lon)` — return `True` if within a configurable
  radius (default 30 nm) of any port whose country is in the
  `SANCTIONED_PORT_COUNTRIES` set already defined in `risk_scoring.py`, OR
  within 30 nm of the hard-coded coordinates of the five major ship-breaking
  yards (Alang, Gadani, Chattogram, Aliağa, Zhoushan) stored as constants in
  the method — no DB seed required for these.
- `_check_in_port_limits(lat, lon)` — return `True` if within 5 km of any port
  in the `ports` table.

Each implementation must be async, use the existing `AsyncSession` already
available in each class, and handle the case where the `ports` table is empty
(fall back to the current hardcoded default with a logged warning).

### R3. Haversine utility
Add a shared haversine distance function in `backend/app/utils/` (reusable across
all three services and any future detection code). The one already in
`spoofing.py` is a standalone function — extract or duplicate it as a proper
utility, and update `spoofing.py` to use it.

### R4. Deliver as 12–15 atomic git commits
Each commit must be self-contained and pass a `git diff --stat` review. Suggested
breakdown (team may reorganise):

1. Add `Port` SQLAlchemy model (`backend/app/models/port.py`)
2. Alembic migration for `ports` table
3. Add haversine utility to `backend/app/utils/geo.py`
4. Update `spoofing.py` to import haversine from the new utility
5. Add ship-breaking yard constants to `backend/app/utils/geo.py`
6. Implement `_is_coastal_position` with PostGIS + haversine fallback
7. Implement `_is_near_risk_zone` (sanctioned ports from DB + yard constants)
8. Implement `_check_in_port_limits`
9. Add `Port` to `backend/app/models/__init__.py` so Alembic detects it
10. Unit tests for haversine utility and distance-threshold logic
11. Unit tests for empty-table fallback behaviour in all three methods
12. Update `DarkVesselDetector` and `STSTransferDetector` docstrings
13. Remove the stale "port_calls has no coordinate columns" comments

## Acceptance Criteria

### Geospatial correctness (unit-testable without a live DB)
- [ ] `haversine_distance(1.35, 103.82, 1.35, 103.82)` returns `0.0`
- [ ] Haversine distance between Singapore (1.35, 103.82) and Rotterdam (51.95, 4.14) is within 1% of 10,300 km
- [ ] `_is_near_risk_zone` returns `True` when called with coordinates within 30 nm of Alang yard (21.41, 72.18) — no DB needed, yard coords are constants
- [ ] `_is_near_risk_zone` returns `False` for open-ocean coordinates far from any yard or sanctioned port

### Database
- [ ] `alembic upgrade head` runs without error on a fresh DB
- [ ] `SELECT COUNT(*) FROM ports` returns `0` on a fresh DB (no seed data)
- [ ] All three methods return the hardcoded fallback (with a logged warning) when the `ports` table is empty — no crash

### Commit hygiene
- [ ] Exactly 12–15 commits between the current HEAD and the branch tip
- [ ] Every commit message follows Conventional Commits (`feat:`, `fix:`, `chore:`, `test:`, `docs:`, `refactor:`)
- [ ] No commit touches more than 3 files
