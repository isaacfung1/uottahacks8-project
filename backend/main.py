"""Main FastAPI application."""
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import pandas as pd
from datetime import datetime

from data_loader import normalize_flights
from sector_logic import mark_sector_membership
from hotspot_detection import detect_hotspots, get_flights_in_bin, CAPACITY_PER_BIN
from probability_engine import enrich_flights, calculate_predicted_load
from recommendations import generate_recommendations, get_flight_explanation
from plan_apply import apply_plan, recompute_metrics
from geojson_utils import create_sector_geojson, create_map_geojson

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state (in production, use database or cache)
flights_df: Optional[pd.DataFrame] = None
STORM_IMPACTED_AIRPORTS = set()  # Can be configured


def initialize_data():
    """Load and process flight data."""
    global flights_df
    
    if flights_df is None:
        # Load and normalize
        import os
        data_path = os.path.join(os.path.dirname(__file__), "canadian_flights_1000.json")
        flights_df = normalize_flights(data_path)
        
        # Mark sector membership
        flights_df = mark_sector_membership(flights_df)
        
        # Enrich with probabilities
        flights_df = enrich_flights(flights_df, STORM_IMPACTED_AIRPORTS)


# Initialize on startup
@app.on_event("startup")
async def startup_event():
    initialize_data()


class PlanRequest(BaseModel):
    selected_hotspot_id: Optional[str] = None
    approved_actions: List[Dict[str, str]]


@app.get("/analyze")
def analyze(bin: Optional[str] = Query(None, description="ISO format datetime for selected bin")):
    """
    Main analysis endpoint.
    
    Returns:
    - sector_geojson
    - map_geojson
    - hotspots[]
    - selected_hotspot
    - metrics (legacy + skyflow)
    - recommended_actions[]
    - flights_in_hotspot[] (table data + explanations)
    """
    global flights_df
    initialize_data()
    
    # Detect hotspots
    hotspots = detect_hotspots(flights_df)
    
    # Parse selected bin if provided
    selected_bin_start = None
    selected_hotspot = None
    if bin:
        try:
            selected_bin_start = pd.to_datetime(bin, utc=True)
            # Find matching hotspot
            for h in hotspots:
                if h['bin_start'] == selected_bin_start:
                    selected_hotspot = h
                    break
        except Exception:
            pass
    
    # If no bin selected, use worst hotspot
    if selected_hotspot is None and hotspots:
        selected_hotspot = hotspots[0]
        selected_bin_start = selected_hotspot['bin_start']
    
    # Get flights in selected bin
    flights_in_bin = pd.DataFrame()
    recommended_actions = []
    flights_table_data = []
    
    if selected_bin_start is not None:
        flights_in_bin = get_flights_in_bin(flights_df, selected_bin_start)
        
        # Generate recommendations
        recommended_actions = generate_recommendations(flights_in_bin)
        
        # Prepare table data with explanations
        for _, flight in flights_in_bin.iterrows():
            explanations = get_flight_explanation(flight)
            is_recommended = any(r['acid'] == flight['acid'] for r in recommended_actions)
            
            flights_table_data.append({
                'acid': flight['acid'],
                'plane_type': flight['plane_type'],
                'passengers': int(flight['passengers']),
                'is_cargo': bool(flight['is_cargo']),
                'arrival_probability': float(flight['arrival_probability']),
                'ghost_flag': bool(flight['ghost_flag']),
                'cost_index': float(flight['cost_index']),
                'is_recommended': is_recommended,
                'explanations': explanations
            })
    
    # Calculate metrics
    legacy_count = 0
    predicted_load = 0.0
    
    if selected_hotspot:
        legacy_count = selected_hotspot['legacy_count']
        predicted_load = calculate_predicted_load(flights_in_bin)
    
    metrics = {
        'legacy': {
            'count': legacy_count,
            'capacity': float(CAPACITY_PER_BIN),
            'status': 'RED' if legacy_count > CAPACITY_PER_BIN * 1.2 else 'YELLOW' if legacy_count > CAPACITY_PER_BIN else 'GREEN',
            'recommendation': 'Ground Stop recommended (mock)' if legacy_count > CAPACITY_PER_BIN else 'Normal operations'
        },
        'skyflow': {
            'predicted_load': float(predicted_load),
            'capacity': float(CAPACITY_PER_BIN),
            'status': 'GREEN' if predicted_load <= CAPACITY_PER_BIN else 'YELLOW' if predicted_load <= CAPACITY_PER_BIN * 1.2 else 'RED',
            'recommendation': 'Surgical plan recommended' if predicted_load > CAPACITY_PER_BIN else 'Normal operations'
        }
    }
    
    # Generate GeoJSON
    sector_geojson = create_sector_geojson()
    map_geojson = create_map_geojson(flights_df, selected_bin_start)
    
    # Format hotspots for JSON (convert timestamps)
    hotspots_formatted = []
    for h in hotspots:
        hotspots_formatted.append({
            'bin_start': h['bin_start'].isoformat(),
            'bin_end': h['bin_end'].isoformat(),
            'legacy_count': int(h['legacy_count']),
            'capacity': float(h['capacity']),
            'severity': float(h['severity'])
        })
    
    return {
        'sector_geojson': sector_geojson,
        'map_geojson': map_geojson,
        'hotspots': hotspots_formatted,
        'selected_hotspot': {
            'bin_start': selected_hotspot['bin_start'].isoformat(),
            'bin_end': selected_hotspot['bin_end'].isoformat(),
            'legacy_count': int(selected_hotspot['legacy_count']),
            'capacity': float(selected_hotspot['capacity']),
            'severity': float(selected_hotspot['severity'])
        } if selected_hotspot else None,
        'metrics': metrics,
        'recommended_actions': recommended_actions,
        'flights_in_hotspot': flights_table_data
    }


@app.post("/plan")
def apply_plan_endpoint(request: PlanRequest):
    """
    Apply approved plan and recompute metrics.
    
    Returns same shape as /analyze but updated.
    """
    global flights_df
    initialize_data()
    
    # Parse selected bin from hotspot_id (assuming it's ISO datetime string)
    selected_bin_start = None
    if request.selected_hotspot_id:
        try:
            selected_bin_start = pd.to_datetime(request.selected_hotspot_id, utc=True)
        except Exception:
            pass
    
    if selected_bin_start is None:
        # Get worst hotspot as default
        hotspots = detect_hotspots(flights_df)
        if hotspots:
            selected_bin_start = hotspots[0]['bin_start']
    
    if selected_bin_start is None:
        return {"error": "No hotspot selected"}
    
    # Apply plan
    flights_df = apply_plan(flights_df, selected_bin_start, request.approved_actions)
    
    # Recompute metrics
    updated_metrics_data = recompute_metrics(flights_df, selected_bin_start)
    
    # Regenerate response (similar to /analyze)
    hotspots = detect_hotspots(flights_df)
    
    selected_hotspot = None
    for h in hotspots:
        if h['bin_start'] == selected_bin_start:
            selected_hotspot = h
            break
    
    # Get flights in bin
    flights_in_bin = get_flights_in_bin(flights_df, selected_bin_start)
    recommended_actions = generate_recommendations(flights_in_bin)
    
    # Prepare table data
    flights_table_data = []
    for _, flight in flights_in_bin.iterrows():
        explanations = get_flight_explanation(flight)
        is_recommended = any(r['acid'] == flight['acid'] for r in recommended_actions)
        
        flights_table_data.append({
            'acid': flight['acid'],
            'plane_type': flight['plane_type'],
            'passengers': int(flight['passengers']),
            'is_cargo': bool(flight['is_cargo']),
            'arrival_probability': float(flight['arrival_probability']),
            'ghost_flag': bool(flight['ghost_flag']),
            'cost_index': float(flight['cost_index']),
            'is_recommended': is_recommended,
            'explanations': explanations,
            'rerouted_flag': bool(flight.get('rerouted_flag', False))
        })
    
    # Update metrics with recomputed values
    metrics = {
        'legacy': {
            'count': updated_metrics_data['legacy_count'],
            'capacity': float(CAPACITY_PER_BIN),
            'status': 'RED' if updated_metrics_data['legacy_count'] > CAPACITY_PER_BIN * 1.2 else 'YELLOW' if updated_metrics_data['legacy_count'] > CAPACITY_PER_BIN else 'GREEN',
            'recommendation': 'Ground Stop recommended (mock)' if updated_metrics_data['legacy_count'] > CAPACITY_PER_BIN else 'Normal operations'
        },
        'skyflow': {
            'predicted_load': updated_metrics_data['predicted_load'],
            'capacity': float(CAPACITY_PER_BIN),
            'status': updated_metrics_data['status'],
            'recommendation': 'Sector relieved' if updated_metrics_data['status'] == 'GREEN' else 'Surgical plan recommended'
        }
    }
    
    # Generate GeoJSON
    sector_geojson = create_sector_geojson()
    map_geojson = create_map_geojson(flights_df, selected_bin_start)
    
    # Format hotspots
    hotspots_formatted = []
    for h in hotspots:
        hotspots_formatted.append({
            'bin_start': h['bin_start'].isoformat(),
            'bin_end': h['bin_end'].isoformat(),
            'legacy_count': int(h['legacy_count']),
            'capacity': float(h['capacity']),
            'severity': float(h['severity'])
        })
    
    return {
        'sector_geojson': sector_geojson,
        'map_geojson': map_geojson,
        'hotspots': hotspots_formatted,
        'selected_hotspot': {
            'bin_start': selected_hotspot['bin_start'].isoformat(),
            'bin_end': selected_hotspot['bin_end'].isoformat(),
            'legacy_count': int(selected_hotspot['legacy_count']),
            'capacity': float(selected_hotspot['capacity']),
            'severity': float(selected_hotspot['severity'])
        } if selected_hotspot else None,
        'metrics': metrics,
        'recommended_actions': recommended_actions,
        'flights_in_hotspot': flights_table_data
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
