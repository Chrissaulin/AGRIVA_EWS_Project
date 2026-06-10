"""
Scaling service for AGRIVA EWS.
Provides scale_input() and unscale_output() utilities for RobustScaler transformation.
"""
from __future__ import annotations

import json
import os
from typing import Any

import pandas as pd


_scaler_stats: dict[str, dict[str, float]] | None = None


def load_scaler_stats(path: str | None = None) -> dict[str, dict[str, float]]:
    """Load scaler statistics from JSON file (cached after first load)."""
    global _scaler_stats
    if _scaler_stats is not None:
        return _scaler_stats

    if path is None:
        path = os.path.join("/app/models_output", "scaler_stats.json")
    if not os.path.exists(path):
        # Fallback to local development path
        path = os.path.join(os.path.dirname(__file__), "..", "..", "01_dapur_jupyter", "models", "scaler_stats.json")
    if not os.path.exists(path):
        path = os.path.join(os.path.dirname(__file__), "..", "..", "scaler_stats.json")

    with open(path, "r") as f:
        _scaler_stats = json.load(f)
    return _scaler_stats


def scale_input(values: dict[str, float], features: list[str] | None = None) -> dict[str, float]:
    """
    Convert real-world values to scaled (z-score) values using RobustScaler parameters.
    
    Formula: scaled = (value - center) / scale
    
    Args:
        values: Dictionary of feature_name -> real value
        features: Optional list of features to scale. If None, uses all known features.
    
    Returns:
        Dictionary with scaled values (features without stats are passed through unchanged)
    """
    stats = load_scaler_stats()
    if features is None:
        features = list(stats.keys())

    result = {}
    for feat in features:
        # Skip features not in scaler stats (e.g., month_extracted, derived columns)
        if feat not in stats:
            result[feat] = values.get(feat, 0)
            continue
        center = stats[feat]["center"]
        scale = stats[feat]["scale"]
        val = values.get(feat, center)
        if val is None:
            val = center
        result[feat] = (float(val) - center) / scale
    return result


def unscale_output(values: dict[str, float | list[float]], features: list[str] | None = None) -> dict[str, float | list[float]]:
    """
    Convert scaled (z-score) values back to real-world values.
    Handles both single values and lists.
    
    Formula: actual = scaled * scale + center
    
    Args:
        values: Dictionary of feature_name -> scaled value (float or list of floats)
        features: Optional list of features to unscale. If None, uses all known features.
    
    Returns:
        Dictionary with real-world values rounded appropriately (features without stats pass through)
    """
    stats = load_scaler_stats()
    if features is None:
        features = list(stats.keys())

    result = {}
    for feat in features:
        # Skip features not in scaler stats (pass through unchanged)
        if feat not in stats:
            result[feat] = values.get(feat, 0 if not isinstance(values.get(feat), list) else [])
            continue

        center = stats[feat]["center"]
        scale = stats[feat]["scale"]
        val = values.get(feat, 0)
        if val is None:
            val = 0
        
        if isinstance(val, list):
            actual = [float(v) * scale + center for v in val]
            if feat in ["Rainfall", "Solar Radiation", "Temperature", "Water Satisfaction Index (WSI)", "FPAR"]:
                result[feat] = [round(a, 2) for a in actual]
            else:
                result[feat] = [round(a, 4) for a in actual]
        else:
            actual = float(val) * scale + center
            if feat in ["Rainfall", "Solar Radiation", "Temperature", "Water Satisfaction Index (WSI)", "FPAR"]:
                result[feat] = round(actual, 2)
            else:
                result[feat] = round(actual, 4)
    return result