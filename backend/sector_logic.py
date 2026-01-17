"""Sector membership detection module."""
from typing import List, Tuple
import math


# Eastern Ontario sector waypoints
SECTOR_WAYPOINTS = [
    (45.88, -78.031),  # 45.88N/78.031W
    (44.55, -75.22),   # 44.55N/75.22W
    (45.42, -75.69),   # Near Ottawa (45.42N/75.69W)
]

# Haversine distance threshold in kilometers
DISTANCE_THRESHOLD_KM = 50.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth in kilometers.
    """
    # Earth radius in kilometers
    R = 6371.0
    
    # Convert to radians
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    # Haversine formula
    a = (math.sin(delta_phi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance


def is_flight_in_sector(route_points: List[Tuple[float, float]]) -> bool:
    """
    Determine if a flight touches the Ottawa/Eastern Ontario sector.
    
    A flight is "in sector" if any route waypoint is close to a sector waypoint.
    """
    if not route_points:
        return False
    
    for route_lat, route_lon in route_points:
        for sector_lat, sector_lon in SECTOR_WAYPOINTS:
            distance = haversine_distance(route_lat, route_lon, sector_lat, sector_lon)
            if distance < DISTANCE_THRESHOLD_KM:
                return True
    
    return False


def mark_sector_membership(df):
    """Add in_sector column to dataframe."""
    df['in_sector'] = df['route_points'].apply(is_flight_in_sector)
    return df
