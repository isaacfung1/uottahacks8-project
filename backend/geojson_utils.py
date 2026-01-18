"""GeoJSON generation utilities for map visualization."""
from typing import List, Dict, Any
import pandas as pd


def route_to_linestring(route_points: List[tuple]) -> List[List[float]]:
    """Convert route points to GeoJSON LineString coordinates [lon, lat]."""
    if not route_points:
        return []
    return [[lon, lat] for lat, lon in route_points]


def create_sector_geojson() -> Dict[str, Any]:
    """Create sector GeoJSON polygon (Toronto–Ottawa bounding box for MVP)."""
    # Toronto–Ottawa corridor bounds (approximate)
    sector_bounds = [
        [-80.5, 43.0],  # SW
        [-73.5, 43.0],  # SE
        [-73.5, 46.5],  # NE
        [-80.5, 46.5],  # NW
        [-80.5, 43.0]   # Close polygon
    ]
    
    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [sector_bounds]
        },
        "properties": {
            "name": "Toronto–Ottawa Sector",
            "fillColor": "#FF6B6B",
            "fillOpacity": 0.2,
            "strokeColor": "#FF6B6B",
            "strokeWidth": 2
        }
    }


def _collect_points_from_flights(flights: pd.DataFrame) -> List[List[float]]:
    points = []
    for _, flight in flights.iterrows():
        route_points = flight.get('route_points', []) or []
        for lat, lon in _sample_route_points(route_points, sample_count=3):
            points.append([lon, lat])
    return points


def _centroid(points: List[List[float]]) -> List[float]:
    if not points:
        return []
    lon_sum = sum(p[0] for p in points)
    lat_sum = sum(p[1] for p in points)
    count = len(points)
    return [lon_sum / count, lat_sum / count]


def _sample_route_points(route_points: List[tuple], sample_count: int = 3) -> List[tuple]:
    """Sample a few representative points from a route."""
    if not route_points:
        return []
    if len(route_points) <= sample_count:
        return route_points

    indices = [
        0,
        len(route_points) // 2,
        len(route_points) - 1
    ]
    return [route_points[i] for i in indices]


def create_hotspot_geojson(df: pd.DataFrame, hotspots: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create GeoJSON FeatureCollection for hotspot points.
    Each feature is a centroid of flights within a hotspot bin.
    """
    from datetime import timedelta
    from hotspot_detection import BIN_SIZE_MINUTES

    features = []

    for hotspot in hotspots:
        bin_start = hotspot.get('bin_start')
        if bin_start is None:
            continue
        bin_end = bin_start + timedelta(minutes=BIN_SIZE_MINUTES)

        flights_in_bin = df[
            (df['dep_time_utc'] >= bin_start) &
            (df['dep_time_utc'] < bin_end) &
            (df['in_sector'] == True)
        ]

        points = _collect_points_from_flights(flights_in_bin)
        hotspot_point = _centroid(points)
        if not hotspot_point:
            continue

        severity = float(hotspot.get('severity', 0.0))
        weighted_load = float(hotspot.get('weighted_load', 0.0))
        legacy_count = int(hotspot.get('legacy_count', 0))

        radius = 8 + min(24.0, max(0.0, weighted_load) * 4.0)

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                    "coordinates": hotspot_point
            },
            "properties": {
                "bin_start": bin_start.isoformat(),
                "legacy_count": legacy_count,
                "weighted_load": weighted_load,
                "severity": severity,
                "radius": radius
            }
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features
    }


def create_map_geojson(df: pd.DataFrame, selected_bin_start: pd.Timestamp = None) -> Dict[str, Any]:
    """
    Create GeoJSON FeatureCollection from flights dataframe.
    
    Includes styling flags: in_sector, in_hotspot_bin, ghost_flag, rerouted_flag
    """
    from datetime import timedelta
    from hotspot_detection import BIN_SIZE_MINUTES
    
    features = []

    # Limit to Toronto–Ottawa sector flights
    df = df[df['in_sector'] == True]
    
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
