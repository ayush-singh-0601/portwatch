# 📖 PortWatch — API Reference

PortWatch exposes a clean, modern RESTful and WebSocket API. The API is built with **FastAPI**, featuring automatic OpenAPI schema generation, fully typed Pydantic payloads, and robust async database query operations.

By default, when running the backend service, interactive documentation is available at:
*   **Swagger UI:** `http://localhost:8000/docs`
*   **ReDoc:** `http://localhost:8000/redoc`

---

## ⚓ Base URL

*   **Development REST API:** `http://localhost:8000/api`
*   **Development WebSocket:** `ws://localhost:8000/ws`

---

## 🧭 Authentication & Headers

Currently, the MVP operates in open OSINT mode with no authentication headers required for internal routing. If deployed behind a reverse proxy, standard CORS headers permit communication from the frontend origin `http://localhost:5173`.

---

## 🛣️ API Endpoints

### 1. Vessels (`/api/vessels`)

#### 🔍 List & Search Vessels
*   **Method:** `GET`
*   **Path:** `/api/vessels`
*   **Query Parameters:**
    *   `name` (string, optional) — Filter or fuzzy-search by vessel name
    *   `imo` (integer, optional) — Exact search by 7-digit IMO number
    *   `mmsi` (integer, optional) — Exact search by 9-digit MMSI number
    *   `vessel_type` (string, optional) — Filter by category (e.g. `Cargo`, `Tanker`, `Fishing`)
    *   `flag` (string, optional) — Filter by 3-character ISO flag state (e.g. `PAN`, `LBR`)
    *   `page` (integer, default: `1`) — Pagination page index
    *   `per_page` (integer, default: `20`) — Count of vessels per page

*   **Success Response (200 OK):**
    ```json
    {
      "items": [
        {
          "imo": 9243124,
          "mmsi": 311000123,
          "name": "OCEAN TRADER",
          "flag": "PAN",
          "vessel_type": "Tanker",
          "gross_tonnage": 45000,
          "dwt": 80000,
          "year_built": 2005,
          "call_sign": "HP8932",
          "risk_score": 65
        }
      ],
      "total": 1,
      "page": 1,
      "per_page": 20,
      "pages": 1
    }
    ```

#### ⚓ Get Vessel Detail
*   **Method:** `GET`
*   **Path:** `/api/vessels/{imo}`
*   **Success Response (200 OK):**
    ```json
    {
      "imo": 9243124,
      "mmsi": 311000123,
      "name": "OCEAN TRADER",
      "flag": "PAN",
      "vessel_type": "Tanker",
      "gross_tonnage": 45000,
      "dwt": 80000,
      "year_built": 2005,
      "call_sign": "HP8932",
      "created_at": "2026-06-01T00:00:00Z",
      "updated_at": "2026-06-02T12:00:00Z"
    }
    ```

---

### 2. Vessel Tracking & Maps (`/api/map` & `/api/vessels`)

#### 🗺️ Get Current Positions for Map View
*   **Method:** `GET`
*   **Path:** `/api/map/positions`
*   **Query Parameters:**
    *   `bbox` (string, optional) — Bounding box defined by comma-separated coordinates: `min_lon,min_lat,max_lon,max_lat` (e.g. `100.0,1.0,104.5,6.0`)
    *   `vessel_type` (string, optional) — Filter by vessel category

*   **Success Response (200 OK):**
    ```json
    [
      {
        "mmsi": 311000123,
        "imo": 9243124,
        "name": "OCEAN TRADER",
        "vessel_type": "Tanker",
        "latitude": 1.2833,
        "longitude": 103.8333,
        "speed": 12.4,
        "course": 245.0,
        "heading": 240,
        "nav_status": 0,
        "last_updated": "2026-06-02T19:40:00Z",
        "risk_score": 65
      }
    ]
    ```

#### 📈 Get Historical Tracks
*   **Method:** `GET`
*   **Path:** `/api/vessels/{imo}/positions`
*   **Query Parameters:**
    *   `start_time` (string, optional) — ISO timestamp to start track query
    *   `end_time` (string, optional) — ISO timestamp to end track query
    *   `limit` (integer, default: `500`) — Maximum returned path segments

*   **Success Response (200 OK):**
    ```json
    {
      "imo": 9243124,
      "positions": [
        {
          "time": "2026-06-02T19:00:00Z",
          "latitude": 1.2750,
          "longitude": 103.8200,
          "speed": 12.1,
          "course": 244.5,
          "heading": 242
        },
        {
          "time": "2026-06-02T19:30:00Z",
          "latitude": 1.2800,
          "longitude": 103.8290,
          "speed": 12.3,
          "course": 244.9,
          "heading": 241
        }
      ]
    }
    ```

---

### 3. Ownership & Relations (`/api/vessels/{imo}/ownership`)

#### 🕸️ Resolve Ownership Graph (D3 Force-Directed Format)
*   **Method:** `GET`
*   **Path:** `/api/vessels/{imo}/ownership`
*   **Success Response (200 OK):**
    ```json
    {
      "nodes": [
        { "id": "vessel-9243124", "label": "OCEAN TRADER", "type": "vessel", "imo": 9243124 },
        { "id": "owner-101", "label": "Vanguard Shipping Corp", "type": "company", "country": "LBR" },
        { "id": "parent-202", "label": "Apex Maritime Holdings Ltd", "type": "company", "country": "GRC" }
      ],
      "edges": [
        { "source": "owner-101", "target": "vessel-9243124", "type": "registered_owner", "effective_date": "2020-04-12" },
        { "source": "parent-202", "target": "owner-101", "type": "beneficial_owner", "effective_date": "2020-04-12" }
      ]
    }
    ```

---

### 4. Sanctions Screening (`/api/vessels/{imo}/sanctions`)

#### 🛡️ Fetch Sanctions Screening Dashboard
*   **Method:** `GET`
*   **Path:** `/api/vessels/{imo}/sanctions`
*   **Success Response (200 OK):**
    ```json
    {
      "imo": 9243124,
      "screened_at": "2026-06-02T12:00:00Z",
      "matches": [
        {
          "id": 42,
          "matched_entity_id": 202,
          "matched_entity_name": "APEX MARITIME HOLDINGS LTD",
          "sanctions_list": "OFAC SDN",
          "program": "UKRAINE-EO13661",
          "match_score": 92.5,
          "match_type": "fuzzy",
          "matched_field": "name",
          "aliases": ["APEX HOLDINGS", "APEX GROUP"]
        }
      ]
    }
    ```

#### 🔄 Trigger Fresh Sanctions Scan
*   **Method:** `POST`
*   **Path:** `/api/vessels/{imo}/screen`
*   **Success Response (200 OK):**
    ```json
    {
      "imo": 9243124,
      "status": "completed",
      "matches_found": 1,
      "timestamp": "2026-06-02T19:45:00Z"
    }
    ```

---

### 5. Risk Engine (`/api/vessels/{imo}/risk`)

#### 📊 Get Risk Score Breakdown
*   **Method:** `GET`
*   **Path:** `/api/vessels/{imo}/risk`
*   **Success Response (200 OK):**
    ```json
    {
      "imo": 9243124,
      "total_score": 45,
      "calculated_at": "2026-06-02T19:40:00Z",
      "breakdown": [
        {
          "factor_name": "Sanctioned beneficial owner",
          "points": 30,
          "evidence_description": "Beneficial Owner Apex Maritime Holdings Ltd fuzzy matches APEX MARITIME HOLDINGS LTD on OFAC SDN List (Score: 92.5%)",
          "evidence_link": "/api/vessels/9243124/sanctions"
        },
        {
          "factor_name": "Ship-to-Ship transfer off-port limits",
          "points": 15,
          "evidence_description": "Detected STS transfer with vessel 'NEPTUNE' (IMO: 9110022) lasting 45 minutes on 2026-05-30",
          "evidence_link": null
        }
      ]
    }
    ```

---

### 6. PDF Reports (`/api/vessels/{imo}/report` & `/api/reports`)

#### 📄 Generate Intelligence Report
*   **Method:** `POST`
*   **Path:** `/api/vessels/{imo}/report`
*   **Success Response (200 OK):**
    ```json
    {
      "report_id": "8c5b527f-9b2f-48db-8e67-ea46f555d49a",
      "vessel_imo": 9243124,
      "status": "generated",
      "download_url": "/api/reports/8c5b527f-9b2f-48db-8e67-ea46f555d49a"
    }
    ```

#### ⬇️ Download Generated Report
*   **Method:** `GET`
*   **Path:** `/api/reports/{report_id}`
*   **Headers:**
    *   `Content-Type: application/pdf`
    *   `Content-Disposition: attachment; filename="PortWatch_IntelReport_9243124.pdf"`
*   **Success Response (200 OK):** Binary stream of WeasyPrint generated PDF.

---

## 🔌 WebSocket Endpoint (`/ws/vessels`)

Used by the UI to stream live AIS tracking telemetry into the dashboard map view.

*   **Path:** `ws://localhost:8000/ws/vessels`
*   **Subscribing / Filtering:**
    Clients can submit a JSON message to filter stream parameters (e.g. bounding box coordinate range):
    ```json
    {
      "bbox": [103.5, 1.15, 104.2, 1.45],
      "vessel_types": ["Tanker", "Cargo"]
    }
    ```

*   **Broadcast Format from Server:**
    The WebSocket server streams regular updates matching subscribers' criteria:
    ```json
    {
      "type": "position_update",
      "data": {
        "mmsi": 311000123,
        "imo": 9243124,
        "name": "OCEAN TRADER",
        "latitude": 1.2833,
        "longitude": 103.8333,
        "speed": 12.4,
        "course": 245.0,
        "heading": 240,
        "nav_status": 0,
        "vessel_type": "Tanker",
        "risk_score": 65
      }
    }
    ```

---

## ⚠️ Error Responses

PortWatch employs descriptive, standard HTTP status codes.

| Code | Meaning | Reason |
|---|---|---|
| `400 Bad Request` | Invalid Inputs | Invalid Bounding box, query format, or Pydantic validation error |
| `404 Not Found` | Vessel/Report Missing | The specified `imo` or `report_id` does not exist in the database |
| `500 Internal Server Error` | Backend Failure | Database connectivity loss or PDF rendering failure in WeasyPrint |

Example `404 Not Found` payload:
```json
{
  "detail": "Vessel with IMO 9999999 not found"
}
```
