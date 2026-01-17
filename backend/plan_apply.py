"""Plan approval and application module."""
import pandas as pd
from typing import List, Set, Dict
from datetime import timedelta
from hotspot_detection import get_flights_in_bin, BIN_SIZE_MINUTES


def apply_plan(
    df: pd.DataFrame,
    selected_bin_start: pd.Timestamp,
    approved_actions: List[Dict]
) -> pd.DataFrame:
    """
    Apply approved plan actions and mark flights as rerouted.
    
    Input:
    - df: flights dataframe
    - selected_bin_start: hotspot bin start time
    - approved_actions: list of {acid, action_type}
    
    Returns: updated dataframe with rerouted_flag set
    """
    df = df.copy()
    
    # Initialize rerouted flag
    if 'rerouted_flag' not in df.columns:
        df['rerouted_flag'] = False
    
    # Mark approved flights as rerouted
    approved_acids = {action['acid'] for action in approved_actions}
    df.loc[df['acid'].isin(approved_acids), 'rerouted_flag'] = True
    
    return df


def recompute_metrics(
    df: pd.DataFrame,
    selected_bin_start: pd.Timestamp
) -> Dict:
    """
    Recompute metrics after plan application.
    
    Returns updated metrics including predicted_load with rerouted flights excluded.
    """
    from hotspot_detection import CAPACITY_PER_BIN
    from probability_engine import calculate_predicted_load
    
    # Get flights in bin (excluding rerouted ones)
    bin_flights = get_flights_in_bin(df, selected_bin_start)
    active_flights = bin_flights[~bin_flights['rerouted_flag']]
    
    # Calculate metrics
    legacy_count = len(bin_flights)  # Original count (unchanged)
    predicted_load = calculate_predicted_load(active_flights)  # Reduced load
    
    status = "GREEN" if predicted_load <= CAPACITY_PER_BIN else "YELLOW" if predicted_load <= CAPACITY_PER_BIN * 1.2 else "RED"
    
    return {
        'legacy_count': int(legacy_count),
        'predicted_load': float(predicted_load),
        'capacity': float(CAPACITY_PER_BIN),
        'status': status
    }
