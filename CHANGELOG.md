# Changelog

All notable changes to the PortWatch maritime OSINT platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-08-26

### Added
- **Frontend Live Action Controls**: Interactive buttons in `VesselPanel` for manual risk score recalculation (`/api/vessels/{imo}/risk/calculate`), on-demand sanctions screening (`/api/vessels/{imo}/screen`), and instant PDF intelligence brief export (`/api/vessels/{imo}/report`).
- **Live WebSocket Telemetry Badge**: Navbar indicator displaying real-time WebSocket connection state (green pulsating badge when live feed is connected).
- **Quick Risk Triage Presets**: Sidebar filter shortcuts ("All Vessels", "High Risk 50+", "Tankers & Cargo") for rapid maritime intelligence triage.
- **Factor 11 Loitering Anomaly Check**: Implemented automated loitering detection near ship-breaking yards and high-risk zones (+5 risk points) in `RiskScoringAgent`.
- **Comprehensive Test Suites**:
  - `backend/tests/test_name_matcher.py` (Unicode normalization, rapidfuzz score boundaries, and batch matching fallback).
  - `backend/tests/test_sanctions_agent.py` (multi-stage sanctions screening, exact IMO matches, entity graph screening).
  - `backend/tests/test_intel_report.py` (intel report context preparation, HTML template rendering, risk level categorization).
  - `backend/tests/test_spoofing.py` (impossible speed jump detection and timestamp validations).
  - `backend/tests/test_sts_detection.py` (port limits proximity checks and haversine distance fallbacks).
  - `backend/tests/test_ws.py` (WebSocket connection management, broadcast serialization caching, and bounding box filtering).
  - `backend/tests/test_reports_router.py` (report store bounds checking and traversal rejection).
  - `frontend/src/utils/riskColors.test.js` & `frontend/src/utils/vesselTypes.test.js` (Node-native unit tests for color/type mappings).

### Fixed
- **React Rules of Hooks**: Fixed early return placement in `VesselPanel.jsx` that previously evaluated conditional returns before `useMemo(timeSinceLastSeen)`.
- **Ownership Entity Resolution**: Corrected edge traversal logic in `enriched.py` to resolve beneficial owners and operators from `source_entity` rather than incorrectly overwriting them with target entity names.
- **Null Timestamp Safety**: Added safe fallbacks for uninitialized `vessel.updated_at` timestamps in `enriched.py`.
- **Sanctions Screening Deduplication**: Routed `/api/vessels/{imo}/screen` through `SanctionsScreeningAgent` with clean stale match replacements and multi-stage screening.
- **RapidFuzz Index Lookup**: Fixed entity name retrieval from extraction index in `name_matcher.py` to prevent normalized name collisions.
- **Intel Report Field Mappings**: Fixed field references in `intel_report.html` and eager-loaded `sanctions_entry` in `IntelReportAgent._get_sanctions`.
- **Polygon Ray-Casting**: Added bounds checking for empty or malformed rings (< 3 vertices) in `dark_detection.py` and coordinate validation in `spoofing.py` and `sts_detection.py`.
- **Report Store Memory Management**: Bounded in-memory report store in `reports.py` to prevent unbounded memory growth on long-running servers.

### Performance
- **Name Normalization LRU Cache**: Added `@lru_cache(maxsize=16384)` to `normalize_name` in `name_matcher.py`.
- **DivIcon Cache Capping**: Capped SVG marker icon cache in `VesselMarker.jsx` to prevent DOM node leaks.
- **WebSocket Broadcast Optimization**: Implemented single-pass JSON serialization for unfiltered WebSocket clients.
