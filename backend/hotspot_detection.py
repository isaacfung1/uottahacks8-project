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
    
    # Group by bin
    bin_counts = sector_flights.groupby('bin_start').agg({
        'acid': 'count'
    }).reset_index()
    bin_counts.columns = ['bin_start', 'legacy_count']
    
    # Calculate severity
    bin_counts['capacity'] = CAPACITY_PER_BIN
    bin_counts['severity'] = bin_counts['legacy_count'] - bin_counts['capacity']
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
