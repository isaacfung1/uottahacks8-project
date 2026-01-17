"""Data ingestion and normalization module."""
import pandas as pd
import re
from datetime import datetime
from typing import List, Tuple


def parse_route(route_str: str) -> List[Tuple[float, float]]:
    """
    Parse route string into waypoint list.
    
    Example: "49.97N/110.935W 49.64N/92.114W" -> [(49.97, -110.935), (49.64, -92.114)]
    """
    if not route_str or not route_str.strip():
        return []
    
    waypoints = []
    # Pattern to match "latN/lonW" format
    pattern = r'([\d.]+)([NS])/([\d.]+)([EW])'
    
    matches = re.findall(pattern, route_str)
    for lat_val, lat_dir, lon_val, lon_dir in matches:
        lat = float(lat_val)
        if lat_dir == 'S':
            lat = -lat
        
        lon = float(lon_val)
        if lon_dir == 'W':
            lon = -lon
        
        waypoints.append((lat, lon))
    
    return waypoints


def normalize_flights(json_path: str) -> pd.DataFrame:
    """
    Load and normalize flight data.
    
    Returns DataFrame with columns:
    acid, plane_type, route_points, altitude, dep_airport, arr_airport, 
    dep_time_utc, speed, passengers, is_cargo
    """
    # Load JSON
    df = pd.read_json(json_path)
    
    # Normalize field names
    normalized = pd.DataFrame()
    normalized['acid'] = df['ACID']
    normalized['plane_type'] = df['Plane type']
    normalized['route_points'] = df['route'].apply(parse_route)
    normalized['altitude'] = df['altitude']
    normalized['dep_airport'] = df['departure airport']
    normalized['arr_airport'] = df['arrival airport']
    normalized['dep_time_utc'] = pd.to_datetime(df['departure time'], unit='s', utc=True)
    normalized['speed'] = df['aircraft speed']
    normalized['passengers'] = df['passengers']
    normalized['is_cargo'] = df['is_cargo']
    
    return normalized
