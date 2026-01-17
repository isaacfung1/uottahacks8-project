from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Tuple, Dict, Any
import pandas as pd
import os

app = FastAPI()

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load flight data
current_dir = os.path.dirname(os.path.abspath(__file__))
data_path = os.path.join(current_dir, "canadian_flights_1000.json")
df = pd.read_json(data_path)


def parse_route(route_str: str) -> List[Tuple[float, float]]:
    """
    Parse route string to list of (lat, lon) tuples.
    Example: "50.77N/115.66W" -> [(50.77, -115.66)]
    Example: "49.82N/86.449W 50.18N/71.405W" -> [(49.82, -86.449), (50.18, -71.405)]
    """
    if not route_str or pd.isna(route_str):
        return []
    
    coordinates = []
    waypoints = route_str.strip().split()
    
    for waypoint in waypoints:
        try:
            # Split by '/'
            parts = waypoint.split('/')
            if len(parts) != 2:
                continue
            
            # Parse latitude
            lat_str = parts[0]
            if 'N' in lat_str:
                lat = float(lat_str.replace('N', ''))
            elif 'S' in lat_str:
                lat = -float(lat_str.replace('S', ''))
            else:
                continue
            
            # Parse longitude
            lon_str = parts[1]
            if 'W' in lon_str:
                lon = -float(lon_str.replace('W', ''))
            elif 'E' in lon_str:
                lon = float(lon_str.replace('E', ''))
            else:
                continue
            
            coordinates.append((lat, lon))
        except (ValueError, IndexError):
            continue
    
    return coordinates


@app.get("/")
def read_root():
    return {"message": "Flight Analytics API", "status": "running"}


@app.post("/analyze")
def analyze_flights(request: Dict[str, Any] = None):
    """
    Analyze flights and return GeoJSON features and metrics.
    Returns flight data with parsed routes as GeoJSON.
    """
    # Create GeoJSON features from flight data
    features = []
    for _, row in df.iterrows():
        route_coords = parse_route(row['route'])
        
        if route_coords:
            # Create a LineString feature for each flight route
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[lon, lat] for lat, lon in route_coords]  # GeoJSON uses [lon, lat]
                },
                "properties": {
                    "ACID": row['ACID'],
                    "plane_type": row['Plane type'],
                    "altitude": int(row['altitude']),
                    "departure_airport": row['departure airport'],
                    "arrival_airport": row['arrival airport'],
                    "departure_time": int(row['departure time']),
                    "aircraft_speed": float(row['aircraft speed']),
                    "passengers": int(row['passengers']),
                    "is_cargo": bool(row['is_cargo'])
                }
            }
            features.append(feature)
    
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    
    # Calculate metrics
    metrics = {
        "total_flights": len(df),
        "total_routes_parsed": len(features),
        "avg_altitude": float(df['altitude'].mean()),
        "total_passengers": int(df['passengers'].sum()),
        "cargo_flights": int(df['is_cargo'].sum()),
        "passenger_flights": int((~df['is_cargo']).sum()),
        "unique_aircraft_types": int(df['Plane type'].nunique()),
        "avg_speed": float(df['aircraft speed'].mean())
    }
    
    return {
        "geojson": geojson,
        "metrics": metrics,
        "status": "success"
    }