# PortWatch — Product Requirements Document
**Version:** 0.1 (Draft) | **Status:** Pre-development | **Owner:** TBD

---

## 1. Problem Statement

AIS-based vessel intelligence tools that detect dark shipping, sanctions exposure, and anomalous behaviour (Windward, Pole Star, Lloyd's List Intelligence) cost $100,000+/yr. Coast Guard units, port authorities in developing countries, commodity trading desks under $500M AUM, investigative journalists, and NGO researchers are entirely priced out. No open-source alternative exists that combines real-time AIS, ownership graph resolution, and sanctions screening in a single platform.

---

## 2. Vision

An open-source maritime OSINT platform that gives any analyst, port authority, or compliance officer the same vessel risk intelligence that $100K/yr enterprise tools provide — built entirely on free public data sources.

---

## 3. Target Users

| User | Core Need |
|---|---|
| Port authority (developing nation) | Identify high-risk vessels before they berth |
| Commodity trading compliance desk | Screen vessels before chartering for sanctions exposure |
| Investigative journalist / NGO | Track sanctioned oil flows and ownership chains |
| Academic / OSINT researcher | Reproducible vessel behaviour analysis |
| Maritime law enforcement | Dark vessel and STS transfer alerts |

---

## 4. Core Features (MVP)

### 4.1 Real-time AIS Vessel Map
- Live vessel positions via AISHub WebSocket feed (free, reciprocal sharing model)
- Leaflet map with vessel type, speed, heading, nav status
- Click vessel → trigger full intelligence workflow

### 4.2 Dark Vessel Detection
- Project forward from last known position using constant-velocity model
- Flag vessels silent for 6h (coastal) / 24h (open ocean) outside known terrestrial dead zones
- Dark event log per vessel: start coordinates, duration, end position

### 4.3 Ownership Chain Resolution
- Pull registered owner, ISM manager, and beneficial owner from Equasis (free EU database) + IMO GISIS
- Render full chain as D3 force-directed graph (3–5 ownership layers)
- Detect name and flag changes over vessel history
- Fuzzy company name matching for alias detection

### 4.4 Sanctions Screening
- Screen vessel name, IMO, MMSI, and all ownership-chain entities against:
  - OFAC SDN list (US Treasury, daily XML)
  - EU consolidated sanctions list
  - UN Security Council list
  - OFSI (UK)
- rapidfuzz name matching at ≥85% token sort ratio for transliteration/variation tolerance
- Near-matches flagged with confidence score — not just binary hits

### 4.5 Behaviour Analysis
- STS (ship-to-ship) transfer detection: two vessels ≤500m, ≤2kts, ≥30 min, off-port-limits
- AIS spoofing detection: impossible positional jumps, duplicate MMSI
- Loitering detection: anchorage near sanctioned ports, ship-breaking yards
- Port call history with PSC detention overlay (Paris/Tokyo MOU data)

### 4.6 Risk Score (0–100, fully auditable)
- Deterministic rule-based score — no black-box ML
- Per-factor breakdown with evidence link for every point
- Designed to be defensible to regulators under OFAC guidance

### 4.7 Intelligence Report (PDF)
- Per-vessel report: identity summary, ownership graph, dark event timeline, risk score breakdown, recommended actions
- LLM-assisted narrative prose around deterministic structured data
- Exported via Weasyprint — no headless browser required

---

## 5. Agent Architecture

```
AISIngestAgent          — persistent WebSocket, NMEA decode, TimescaleDB upsert
      ↓
IdentityResolutionAgent — Equasis + IMO GISIS ownership chain, 24h cache
      ↓
SanctionsScreeningAgent — OFAC/EU/UN/OFSI matching, rapidfuzz near-match
      ↓
BehaviorAnalysisAgent   — dark events, STS detection, spoofing, loitering
      ↓
RiskScoringAgent        — 0–100 auditable score, per-factor breakdown
      ↓
IntelReportAgent        — structured PDF report, LLM narrative layer
```

---

## 6. Data Sources (all free)

| Source | Data | Access |
|---|---|---|
| AISHub | Real-time vessel positions | Free (data sharing) |
| Equasis | Ownership, ISM, PSC history | Free (EU-funded, registration) |
| IMO GISIS | Official ship registry | Free |
| OFAC SDN | US sanctions list | Free daily XML |
| EU FISMA | EU consolidated sanctions | Free XML |
| Paris / Tokyo MOU | PSC detentions | Free, scrapeable |
| NOAA AIS archive | Historical US waters AIS | Free |

---

## 7. Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| AIS decode | pyais | Handles all 27 AIS message types |
| Time-series DB | TimescaleDB | Append-heavy positions, auto-compression |
| Geospatial | PostGIS | STS radius queries, port proximity, dead-zone polygons |
| Ownership graph | PostgreSQL + NetworkX | Adjacency list + in-memory graph analysis |
| Name matching | rapidfuzz | 10× faster than fuzzywuzzy, handles transliterations |
| API | FastAPI + async SQLAlchemy | High-throughput AIS write path |
| Frontend | React + Leaflet + D3 | Map + ownership force graph |
| Semantic search | pgvector | Entity name embeddings for fuzzy company queries |
| Report gen | Weasyprint | HTML/CSS → PDF, no Puppeteer |
| Deployment | Docker + Cloud Run | AIS agent as min-instance, API scales to zero |

---

## 8. Risk Score Factor Table

| Factor | Points |
|---|---|
| Beneficial owner on sanctions list | +30 |
| Sanctioned port call (last 12 months) | +20 |
| STS transfer detected at sea | +15 |
| Flag of convenience registry | +15 |
| Dark event (per event, last 90 days) | +5 each |
| PSC detention (last 2 years) | +10 |
| 3+ name or flag changes | +10 |
| Near-match on sanctions list (≥85%) | +10 |
| IMO high-risk flag state | +5 |
| Vessel age over 20 years | +5 |
| Loitering near ship-breaking yard | +5 |

---

## 9. What PortWatch is NOT

- Not a real-time alerting/monitoring SaaS (MVP is search-driven, not push-alert)
- Not a satellite AIS aggregator (terrestrial AIS only in MVP, satellite as future enhancement)
- Not a vessel certification or flag state compliance tool
- Not a replacement for full maritime legal due diligence

---

## 10. MVP Milestones

| Milestone | Deliverable |
|---|---|
| M1 — Data foundation | AIS ingest pipeline live, TimescaleDB schema, Equasis scraper |
| M2 — Core agents | IdentityResolution + SanctionsScreening agents working |
| M3 — Map UI | Leaflet map + vessel detail panel + ownership D3 graph |
| M4 — Risk engine | BehaviorAnalysis + RiskScoring with auditable factor breakdown |
| M5 — Reports | PDF intelligence report generation + LLM narrative layer |
| M6 — Public launch | GitHub release + first published open-source vessel investigation |

---

## 11. Success Metrics (6 months post-launch)

- 500+ GitHub stars
- At least one published investigation using PortWatch data
- ≥3 external contributors
- Risk score validated against 10 known-sanctioned vessels (ground truth from OFAC cases)

---

*PortWatch is open-source. All data sources used are public and free. The tool does not facilitate harm — it surfaces publicly available sanctions and ownership information that compliance professionals are legally required to check.*
