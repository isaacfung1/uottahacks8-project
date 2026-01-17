"""GeoJSON generation utilities for map visualization."""
from typing import List, Dict, Any
import pandas as pd


def route_to_linestring(route_points: List[tuple]) -> List[List[float]]:
    """Convert route points to GeoJSON LineString coordinates [lon, lat]."""
    if not route_points:
        return []
    return [[lon, lat] for lat, lon in route_points]


def create_sector_geojson() -> Dict[str, Any]:
    """Create sector GeoJSON polygon (simplified as bounding box for MVP)."""
    # Eastern Ontario sector bounds (simplified)
    sector_bounds = [
        [-78.5, 44.0],  # SW
        [-75.0, 44.0],  # SE
        [-75.0, 46.5],  # NE
        [-78.5, 46.5],  # NW
        [-78.5, 44.0]   # Close polygon
    ]
    
    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [sector_bounds]
        },
        "properties": {
            "name": "Eastern Ontario Sector",
            "fillColor": "#FF6B6B",
            "fillOpacity": 0.2,
            "strokeColor": "#FF6B6B",
            "strokeWidth": 2
        }
    }


def create_map_geojson(df: pd.DataFrame, selected_bin_start: pd.Timestamp = None) -> Dict[str, Any]:
    """
    Create GeoJSON FeatureCollection from flights dataframe.
    
    Includes styling flags: in_sector, in_hotspot_bin, ghost_flag, rerouted_flag
    """
    from datetime import timedelta
    from hotspot_detection import BIN_SIZE_MINUTES
    
    features = []
    
    for _, flight in df.iterrows():
        route_coords = route_to_linestring(flight['route_points'])
        
        if not route_coords:
            continue
        
        # Determine if in selected hotspot bin
        in_hotspot_bin = False
        if selected_bin_start is not None:
            bin_end = selected_bin_start + timedelta(minutes=BIN_SIZE_MINUTES)
            in_hotspot_bin = (
                flight['dep_time_utc'] >= selected_bin_start and
                flight['dep_time_utc'] < bin_end and
                flight['in_sector'] == True
            )
        
        # Styling properties
        properties = {
            "acid": flight['acid'],
            "plane_type": flight['plane_type'],
            "in_sector": bool(flight['in_sector']),
            "in_hotspot_bin": in_hotspot_bin,
            "ghost_flag": bool(flight.get('ghost_flag', False)),
            "rerouted_flag": bool(flight.get('rerouted_flag', False)),
            "arrival_probability": float(flight.get('arrival_probability', 0.85)),
            "cost_index": float(flight.get('cost_index', 0)),
        }
        
        # Determine stroke style based on flags
        if flight.get('rerouted_flag', False):
            properties['strokeColor'] = "#FFA500"
            properties['strokeWidth'] = 3
            properties['strokeDashArray'] = "5,5"
        elif in_hotspot_bin:
            properties['strokeColor'] = "#FF0000"
            properties['strokeWidth'] = 2.5
        elif flight.get('ghost_flag', False):
            properties['strokeColor'] = "#CCCCCC"
            properties['strokeWidth'] = 1
            properties['strokeOpacity'] = 0.4
        else:
            properties['strokeColor'] = "#0066FF"
            properties['strokeWidth'] = 1.5
        
        feature = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": route_coords
            },
            "properties": properties
        }
        
        features.append(feature)
    
    return {
        "type": "FeatureCollection",
        "features": features
    }
