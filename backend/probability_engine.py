"""Probabilistic enrichment module."""
import pandas as pd
from typing import List, Set


# Baseline arrival probability
BASELINE_PROBABILITY = 0.85

# Adjustment factors
CARGO_BOOST = 0.05
LOW_PRIORITY_PENALTY = -0.10
REGIONAL_PENALTY = -0.05
STORM_IMPACT_PENALTY = -0.25

# Probability bounds
MIN_PROBABILITY = 0.05
MAX_PROBABILITY = 0.98

# Ghost flag threshold
GHOST_THRESHOLD = 0.5

# Cost index weights
PASSENGER_WEIGHT = 1.0
CARGO_BONUS = 150


# Aircraft classifications (simplified)
REGIONAL_TYPES = {'Dash 8', 'Embraer', 'CRJ', 'Q400'}


def is_regional(plane_type: str) -> bool:
    """Check if plane type is regional."""
    return any(regional in plane_type for regional in REGIONAL_TYPES)


def calculate_arrival_probability(
    is_cargo: bool,
    passengers: int,
    plane_type: str,
    dep_airport: str,
    storm_impacted_airports: Set[str]
) -> float:
    """
    Calculate arrival probability using deterministic rules.
    
    Rules:
    - Baseline: 0.85
    - If is_cargo: +0.05
    - If passengers == 0 and not cargo: -0.10
    - If regional plane: -0.05
    - If departure airport is storm-impacted: -0.25
    """
    p = BASELINE_PROBABILITY
    
    if is_cargo:
        p += CARGO_BOOST
    
    if passengers == 0 and not is_cargo:
        p += LOW_PRIORITY_PENALTY
    
    if is_regional(plane_type):
        p += REGIONAL_PENALTY
    
    if dep_airport in storm_impacted_airports:
        p += STORM_IMPACT_PENALTY
    
    # Clamp to bounds
    p = max(MIN_PROBABILITY, min(MAX_PROBABILITY, p))
    
    return p


def calculate_cost_index(passengers: int, is_cargo: bool, plane_type: str) -> float:
    """
    Calculate cost index (relative, not dollars).
    
    cost_index = passengers * weight + cargo_bonus
    Optionally multiply by aircraft class (simplified for MVP).
    """
    base_cost = passengers * PASSENGER_WEIGHT
    
    if is_cargo:
        base_cost += CARGO_BONUS
    
    # Optional: multiply by aircraft class (simplified)
    # Widebody > narrowbody > regional
    if '787' in plane_type or '777' in plane_type or '767' in plane_type:
        multiplier = 1.5
    elif '737' in plane_type or 'A320' in plane_type or 'A321' in plane_type:
        multiplier = 1.0
    else:
        multiplier = 0.8
    
    return base_cost * multiplier


def enrich_flights(df: pd.DataFrame, storm_impacted_airports: Set[str] = None) -> pd.DataFrame:
    """
    Add probabilistic fields to flights.
    
    Adds: arrival_probability, ghost_flag, cost_index
    """
    if storm_impacted_airports is None:
        storm_impacted_airports = set()
    
    df = df.copy()
    
    df['arrival_probability'] = df.apply(
        lambda row: calculate_arrival_probability(
            row['is_cargo'],
            row['passengers'],
            row['plane_type'],
            row['dep_airport'],
            storm_impacted_airports
        ),
        axis=1
    )
    
    df['ghost_flag'] = df['arrival_probability'] < GHOST_THRESHOLD
    
    df['cost_index'] = df.apply(
        lambda row: calculate_cost_index(
            row['passengers'],
            row['is_cargo'],
            row['plane_type']
        ),
        axis=1
    )
    
    return df


def calculate_predicted_load(df: pd.DataFrame) -> float:
    """
    Calculate predicted load for a hotspot bin.
    
    predicted_load = sum(arrival_probability for flights in bin)
    """
    if df.empty:
        return 0.0
    return df['arrival_probability'].sum()
