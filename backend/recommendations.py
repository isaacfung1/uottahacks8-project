"""Recommendation engine module."""
import pandas as pd
from typing import List, Dict


EPSILON = 0.01  # Small value to avoid division by zero
MAX_RECOMMENDATIONS = 2


def generate_recommendations(flights_in_bin: pd.DataFrame) -> List[Dict]:
    """
    Propose surgical actions to relieve congestion.
    
    For each flight:
    - impact = arrival_probability (contribution to congestion)
    - penalty = cost_index (cost to move)
    - score = impact / (penalty + epsilon)
    
    Select top N flights with highest score (excluding ghost flights).
    """
    if flights_in_bin.empty:
        return []
    
    # Filter out ghost flights
    candidate_flights = flights_in_bin[~flights_in_bin['ghost_flag']].copy()
    
    if candidate_flights.empty:
        return []
    
    # Calculate score
    candidate_flights['score'] = (
        candidate_flights['arrival_probability'] / 
        (candidate_flights['cost_index'] + EPSILON)
    )
    
    # Sort by score (highest first)
    candidate_flights = candidate_flights.sort_values('score', ascending=False)
    
    # Select top N
    top_flights = candidate_flights.head(MAX_RECOMMENDATIONS)
    
    # Generate recommendations
    recommendations = []
    for _, flight in top_flights.iterrows():
        explanations = []
        
        explanations.append(
            f"High expected contribution to sector load (p={flight['arrival_probability']:.2f})"
        )
        explanations.append(
            f"Lower cost to reroute than alternatives (cost_index={flight['cost_index']:.1f})"
        )
        explanations.append("Not flagged as ghost flight")
        
        recommendations.append({
            'acid': flight['acid'],
            'action_type': 'reroute',
            'score': float(flight['score']),
            'explanations': explanations
        })
    
    return recommendations


def get_flight_explanation(flight: pd.Series) -> List[str]:
    """Generate explanation for why a flight was or wasn't selected."""
    explanations = []
    
    explanations.append(f"Aircraft: {flight['plane_type']}")
    explanations.append(f"Route: {len(flight['route_points'])} waypoints")
    explanations.append(f"Arrival probability: {flight['arrival_probability']:.2f}")
    explanations.append(f"Cost index: {flight['cost_index']:.1f}")
    
    if flight['ghost_flag']:
        explanations.append("⚠️ Flagged as ghost flight (low arrival probability)")
    
    if flight['is_cargo']:
        explanations.append("✓ Cargo flight (higher reliability)")
    
    return explanations
