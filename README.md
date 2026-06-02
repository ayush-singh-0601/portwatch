# ⚓ PortWatch

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Tech Stack: FastAPI & React](https://img.shields.io/badge/Stack-FastAPI%20%2B%20React-darkgreen.svg)](#tech-stack)
[![Status: MVP Complete](https://img.shields.io/badge/Status-MVP%20Complete-success.svg)](#milestones)

An open-source maritime OSINT (Open Source Intelligence) platform designed to give analysts, port authorities, investigative journalists, and compliance officers the same high-caliber vessel risk intelligence that enterprise tools ($100K+/yr) provide—built entirely on free and public data sources.

---

## 🧭 Overview

PortWatch combines real-time AIS decoding, multi-source sanctions screening, automated ownership graph resolution, and geospatial behavioral risk analysis (dark events, STS transfers) into a unified, high-performance platform.

### Core Architecture Flow
```
[ AIS Ingest & NMEA Decode ] (AISStream WebSocket / pyais)
             │
             ▼
[ Identity Resolution Agent ] (Registered/Beneficial Owners, Equasis & GISIS)
             │
             ▼
[ Sanctions Screening Agent ] (OFAC SDN, EU, UN, OFSI fuzzy name match >=85%)
             │
             ▼
[ Behavior Analysis Agent ] (Dark events, STS transfers, AIS spoofing, loitering)
             │
             ▼
[ Risk Scoring Agent ] (Deterministic, fully auditable 0-100 score & breakdown)
             │
             ▼
[ Intel Report Agent ] (PDF Generation with WeasyPrint + optional LLM narrative)
```

---

## ✨ Features

*   **Real-time AIS Vessel Map:** Live positions visualized on an interactive dark-themed Leaflet map. Custom ship-shaped SVG markers dynamically colored by vessel category and oriented according to heading.
*   **Dark Vessel Detection:** Detects and logs when a vessel turns off its AIS transceiver (silent for 6h coastal / 24h open ocean) outside known terrestrial dead zones.
*   **Ship-to-Ship (STS) Transfer Alerts:** Identifies potential STS transfers based on geospatial proximity (vessels within 500m, travelling <2kts, for over 30 minutes, off-port-limits).
*   **Ownership Graph Resolution:** Renders complex 3–5 layer maritime ownership chains (Registered Owner, ISM Manager, Beneficial Owner) in a responsive **D3 force-directed graph** featuring interactive drag, zoom, and relationship mapping.
*   **Comprehensive Sanctions Screening:** Fuzzy name matching (via `rapidfuzz` token sort ratio) against:
    *   US OFAC SDN List (daily XML feed)
    *   EU Consolidated Sanctions List
    *   UN Security Council Sanctions List
    *   UK OFSI Sanctions List
*   **Deterministic Risk Scoring:** A fully auditable 0–100 risk score breakdown with evidence descriptions and links, strictly adhering to regulatory compliance frameworks.
*   **Premium PDF Intelligence Reports:** Exquisite, A4-styled, print-perfect intelligence briefs generated directly via **WeasyPrint** and Jinja2 with clean page breaks and an optional LLM-assisted analysis narrative.

---

## 🛠️ Tech Stack

### Backend
*   **Language & Framework:** Python 3.12, FastAPI (async/await)
*   **Database:** PostgreSQL with **TimescaleDB** (time-series AIS positions) and **PostGIS** (geospatial queries)
*   **Graph Processing:** NetworkX
*   **Name Matching:** RapidFuzz (C-optimized Levenshtein & Token Sort)
*   **Reporting:** WeasyPrint + Jinja2 (HTML-to-PDF rendering without a headless browser)

### Frontend
*   **Language & Framework:** TypeScript, React 19, Vite
*   **Mapping:** Leaflet & React-Leaflet
*   **Visualizations:** D3.js (Force-directed graphs)
*   **Styling:** Custom Vanilla CSS for a premium glassmorphic, dark maritime aesthetic

---

## 🚀 Quick Start

The quickest way to spin up the entire PortWatch ecosystem (Database, Backend, and Frontend) is using **Docker Compose**.

### Prerequisites
*   Docker & Docker Compose
*   An API key from [AISStream.io](https://aisstream.io/) (Optional, mock data mode is active by default)

### 1. Configure Environment
Clone the repository and copy the environment template:
```bash
cp .env.example .env
```

Open `.env` and set up your configurations:
*   `DATABASE_URL` (Defaults to internal compose connection)
*   `AISSTREAM_API_KEY` (Optional)
*   `MOCK_DATA_MODE=True` (Keep True to seed and run with realistic test data)

### 2. Launch with Docker Compose
Start the service container cluster:
```bash
docker-compose up --build -d
```
This launches:
*   **Database:** TimescaleDB + PostGIS on port `5432`
*   **Backend:** FastAPI API server on port `8000`
*   **Frontend:** React dev server on port `5173`

### 3. Seed Mock Data (If running locally or using mock mode)
Once the containers are running, populate the database with 100 realistic vessels, ownership chains, historic track points, dark events, STS interactions, and sanctions matches:
```bash
docker-compose exec backend python -m seed.generate_mock_data
```

Access the dashboard at `http://localhost:5173`.

---

## 💻 Manual Setup (Development)

If you prefer to run the services bare-metal:

### Backend Setup
1.  Navigate to the backend directory:
    ```bash
    cd backend
    ```
2.  Create and activate a virtual environment:
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate
    # On Unix/macOS
    source venv/bin/activate
    ```
3.  Install dependencies:
    ```bash
    pip install -e .
    ```
4.  Run database migrations:
    ```bash
    alembic upgrade head
    ```
5.  Seed data:
    ```bash
    python -m seed.generate_mock_data
    ```
6.  Start the FastAPI application:
    ```bash
    uvicorn app.main:app --reload
    ```

### Frontend Setup
1.  Navigate to the frontend directory:
    ```bash
    cd frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Launch the development server:
    ```bash
    npm run dev
    ```

---

## 📂 Project Structure

```
├── backend/                  # FastAPI Application
│   ├── app/
│   │   ├── agents/           # Identity, Sanctions, Risk, & Report Agents
│   │   ├── models/           # SQLAlchemy DB Models (TimescaleDB/PostGIS)
│   │   ├── routers/          # API Handlers & WebSockets
│   │   ├── schemas/          # Pydantic Schemas
│   │   ├── services/         # AIS Stream, Name Matcher, PDF Reports
│   │   └── templates/        # HTML Templates for Reports (WeasyPrint)
│   ├── seed/                 # Synthetic Data Generation Scripts
│   ├── Dockerfile
│   └── pyproject.toml
├── frontend/                 # Vite & React SPA
│   ├── src/
│   │   ├── components/       # Custom Glassmorphic Cards, Search, Badges
│   │   ├── hooks/            # Live WebSocket Map Handlers
│   │   └── styles/           # Deep Dark Maritime Design Tokens
│   ├── index.html
│   └── package.json
├── docker-compose.yml        # Multi-container orchestration
└── PortWatch_PRD.md          # Original Product Requirements Document
```

---

## 📝 License & Contributing

PortWatch is open-source software licensed under the [AGPL-3.0 License](LICENSE).

We welcome contributions of all forms:
*   Geospatial analysis heuristics (new risk indicators)
*   Integrations for additional open registries
*   Fuzzy name matching enhancements
*   Performance updates on the TimescaleDB tracking pipeline

Check out [CONTRIBUTING.md](CONTRIBUTING.md) for details on code style, linting, and PR submissions.

---

⚓ **PortWatch** — *Empowering global compliance, OSINT journalists, and port authorities with absolute transparency in international shipping.*
