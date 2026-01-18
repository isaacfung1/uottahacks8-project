"""Time window binning and hotspot detection module."""
import pandas as pd
from datetime import timedelta
from typing import List, Dict


BIN_SIZE_MINUTES = 10
CAPACITY_PER_HOUR = 15
CAPACITY_PER_BIN = CAPACITY_PER_HOUR * (BIN_SIZE_MINUTES / 60.0)  # 2.5 for 10-min bins


def floor_to_bin(dt: pd.Timestamp) -> pd.Timestamp:
    """Floor datetime to nearest bin (e.g., 10 minutes)."""
    minutes = dt.minute
    bin_minute = (minutes // BIN_SIZE_MINUTES) * BIN_SIZE_MINUTES
    return dt.replace(minute=bin_minute, second=0, microsecond=0)


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _flight_contribution(row: pd.Series) -> float:
    """
    Weighted contribution of a flight to congestion.

    Uses route length, arrival probability, speed, and altitude.
    """
    route_len = len(row.get('route_points', []) or [])
    arrival_probability = _safe_float(row.get('arrival_probability', 0.85), 0.85)
    speed = _safe_float(row.get('speed', 0.0), 0.0)
    altitude = _safe_float(row.get('altitude', 0.0), 0.0)

    # Normalize crude scales to ~[0,1]
    route_factor = min(route_len / 10.0, 1.0)
    speed_factor = min(speed / 900.0, 1.0)
    altitude_factor = min(altitude / 40000.0, 1.0)

    return arrival_probability * (
        0.4 * route_factor +
        0.3 * speed_factor +
        0.3 * altitude_factor
    )


def _dynamic_capacity(flights_in_bin: pd.DataFrame) -> float:
    """
    Compute a dynamic capacity multiplier based on traffic complexity.

    Higher variance/mix -> lower capacity.
    """
    base = CAPACITY_PER_BIN
    if flights_in_bin.empty:
        return base

    speed_std = float(flights_in_bin['speed'].std() or 0.0)
    altitude_std = float(flights_in_bin['altitude'].std() or 0.0)
    type_mix = float(flights_in_bin['plane_type'].nunique() / max(len(flights_in_bin), 1))

    ghost_ratio = float(flights_in_bin.get('ghost_flag', pd.Series([0] * len(flights_in_bin))).mean() or 0.0)
    reroute_ratio = float(flights_in_bin.get('rerouted_flag', pd.Series([0] * len(flights_in_bin))).mean() or 0.0)

    # Normalize to 0..1
    speed_norm = min(speed_std / 150.0, 1.0)
    altitude_norm = min(altitude_std / 5000.0, 1.0)
    mix_norm = min(type_mix / 0.6, 1.0)
    ghost_norm = min(ghost_ratio / 0.5, 1.0)
    reroute_norm = min(reroute_ratio / 0.3, 1.0)

    penalty = (
        0.25 * speed_norm +
        0.20 * altitude_norm +
        0.20 * mix_norm +
        0.20 * ghost_norm +
        0.15 * reroute_norm
    )

    multiplier = 1.05 - penalty
    multiplier = min(max(multiplier, 0.6), 1.1)

    return base * multiplier


def detect_hotspots(df: pd.DataFrame) -> List[Dict]:
    """
    Detect hotspots by counting flights per time bin in the sector.
    
    Returns sorted list of hotspots with highest severity first.
    """
    # Filter flights in sector
    sector_flights = df[df['in_sector'] == True].copy()
    
    if sector_flights.empty:
        return []
    
    # Create bins
    sector_flights['bin_start'] = sector_flights['dep_time_utc'].apply(floor_to_bin)
    sector_flights['bin_end'] = sector_flights['bin_start'] + timedelta(minutes=BIN_SIZE_MINUTES)

    # Weighted contribution per flight
    sector_flights['contribution'] = sector_flights.apply(_flight_contribution, axis=1)
    
    # Group by bin
    bin_counts = sector_flights.groupby('bin_start').agg({
        'acid': 'count',
        'contribution': 'sum'
    }).reset_index()
    bin_counts.columns = ['bin_start', 'legacy_count', 'weighted_load']
    
    # Dynamic capacity per bin
    capacity_by_bin = (
        sector_flights.groupby('bin_start')
        .apply(_dynamic_capacity)
        .rename('capacity')
        .reset_index()
    )

    bin_counts = bin_counts.merge(capacity_by_bin, on='bin_start', how='left')

    # Sanitize capacity/weighted load
    bin_counts['capacity'] = bin_counts['capacity'].fillna(CAPACITY_PER_BIN)
    bin_counts['capacity'] = bin_counts['capacity'].replace([pd.NA, pd.NaT], CAPACITY_PER_BIN)
    bin_counts['capacity'] = bin_counts['capacity'].astype(float)
    bin_counts['weighted_load'] = bin_counts['weighted_load'].fillna(0.0).astype(float)

    # Calculate severity as percent of capacity (0-100)
    bin_counts['severity'] = (bin_counts['weighted_load'] / bin_counts['capacity']) * 100.0
    bin_counts['severity'] = bin_counts['severity'].replace([float('inf'), -float('inf')], 0.0)
    bin_counts['severity'] = bin_counts['severity'].fillna(0.0).clip(lower=0, upper=100)
    bin_counts['bin_end'] = bin_counts['bin_start'] + timedelta(minutes=BIN_SIZE_MINUTES)
    
    # Sort by severity (highest first)
    bin_counts = bin_counts.sort_values('severity', ascending=False)
    
    # Convert to list of dicts
    hotspots = bin_counts.to_dict('records')
    
    return hotspots


def get_flights_in_bin(df: pd.DataFrame, bin_start: pd.Timestamp) -> pd.DataFrame:
    """Get all flights in a specific bin."""
    bin_end = bin_start + timedelta(minutes=BIN_SIZE_MINUTES)
    mask = (
        (df['dep_time_utc'] >= bin_start) &
        (df['dep_time_utc'] < bin_end) &
        (df['in_sector'] == True)
    )
    return df[mask].copy()
