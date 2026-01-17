# SkyFlow - Air Traffic Management MVP

A complete MVP implementation for intelligent air traffic congestion management using probabilistic modeling and surgical rerouting recommendations.

## Features

### Backend (FastAPI + Python)

1. **Data Ingestion & Normalization** (`data_loader.py`)
   - Loads JSON flight data
   - Parses route strings into waypoint coordinates
   - Normalizes field names and converts timestamps

2. **Sector Membership Detection** (`sector_logic.py`)
   - Detects flights touching Ottawa/Eastern Ontario sector
   - Uses Haversine distance calculation (50km threshold)

3. **Hotspot Detection** (`hotspot_detection.py`)
   - 10-minute time binning
   - Identifies congestion hotspots by counting flights per bin
   - Calculates severity scores

4. **Probabilistic Enrichment** (`probability_engine.py`)
   - Calculates arrival probability using deterministic rules
   - Flags ghost flights (low arrival probability)
   - Computes cost index for rerouting decisions

5. **Recommendation Engine** (`recommendations.py`)
   - Proposes surgical actions to relieve congestion
   - Scores flights by impact vs cost ratio
   - Generates explainable recommendations

6. **Plan Application** (`plan_apply.py`)
   - Applies approved rerouting actions
   - Recomputes metrics after plan execution
   - Updates flight status flags

7. **API Endpoints** (`main.py`)
   - `GET /analyze?bin=<optional>` - Full analysis with hotspots, recommendations, and GeoJSON
   - `POST /plan` - Apply approved actions and recompute

### Frontend (React + Leaflet)

1. **Map Visualization**
   - Interactive Leaflet map with GeoJSON flight routes
   - Sector overlay highlighting Eastern Ontario region
   - Color-coded flight styling (normal, hotspot, ghost, rerouted)

2. **Metrics Dashboard**
   - Side-by-side comparison: Legacy vs SkyFlow metrics
   - Status badges (GREEN/YELLOW/RED)
   - Capacity visualization

3. **Hotspot Panel**
   - List of detected hotspots sorted by severity
   - Click to select and analyze specific time bin
   - Shows legacy count and severity scores

4. **Flight Table**
   - Detailed list of flights in selected hotspot
   - Shows arrival probability, ghost flags, cost index
   - Highlights recommended actions

5. **Flight Details Panel**
   - Expandable explanation for each flight
   - Shows why flights were/were not selected for rerouting
   - Full probabilistic reasoning display

6. **Approval Flow**
   - One-click approval of recommended actions
   - Real-time metric updates after approval
   - Visual feedback on sector relief

7. **Timeline Chart**
   - Visual demand over time
   - Shows legacy count, predicted load, and capacity line
   - Highlights selected hotspot bin

## Getting Started

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will run on `http://localhost:5173` (or Vite's default port).
The backend API will be available at `http://localhost:8000`.

## API Contract

### GET /analyze?bin=<optional>

Returns complete analysis including:
- `sector_geojson`: Sector boundary polygon
- `map_geojson`: All flights as LineString features with styling properties
- `hotspots[]`: List of congestion hotspots sorted by severity
- `selected_hotspot`: Currently selected hotspot bin details
- `metrics`: Legacy and SkyFlow comparison metrics
- `recommended_actions[]`: Proposed rerouting actions
- `flights_in_hotspot[]`: Table data with explanations

### POST /plan

Body:
```json
{
  "selected_hotspot_id": "2025-12-01T10:00:00Z",
  "approved_actions": [
    {"acid": "ACA123", "action_type": "reroute"}
  ]
}
```

Returns same shape as `/analyze` but with updated metrics after applying the plan.

## Data Format

Flight data is loaded from `backend/canadian_flights_1000.json` with the following structure:
- ACID: Flight identifier
- Plane type: Aircraft type
- route: Space-separated waypoints (e.g., "46.15N/84.33W 49.97N/110.935W")
- departure time: Unix UTC timestamp
- passengers, is_cargo: Load information

## Sector Definition

Eastern Ontario sector waypoints:
- 45.88N/78.031W
- 44.55N/75.22W
- 45.42N/75.69W (near Ottawa)

Flights are considered "in sector" if any route waypoint is within 50km of a sector waypoint.

## Probabilistic Rules

Arrival probability starts at 0.85 baseline:
- +0.05 if cargo (more reliable)
- -0.10 if passengers == 0 and not cargo (low priority)
- -0.05 if regional aircraft (more cancellations)
- -0.25 if departure airport is storm-impacted

Ghost flights: arrival_probability < 0.5

Cost index = passengers × 1.0 + cargo_bonus (150) × aircraft_class_multiplier
